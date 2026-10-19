from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404

from .forms import JobForm, JobSearchForm
from .models import Job, SavedJob


def job_list_view(request):
    jobs = Job.objects.filter(status=Job.Status.OPEN).select_related("client", "category")
    form = JobSearchForm(request.GET or None)

    if form.is_valid():
        q = form.cleaned_data.get("q")
        category = form.cleaned_data.get("category")
        location = form.cleaned_data.get("location")
        min_budget = form.cleaned_data.get("min_budget")
        max_budget = form.cleaned_data.get("max_budget")
        sort = form.cleaned_data.get("sort") or "-created_at"

        if q:
            jobs = jobs.filter(title__icontains=q)
        if category:
            jobs = jobs.filter(category=category)
        if location:
            jobs = jobs.filter(location__icontains=location)
        if min_budget:
            jobs = jobs.filter(budget__gte=min_budget)
        if max_budget:
            jobs = jobs.filter(budget__lte=max_budget)

        if sort == "budget_desc":
            jobs = jobs.order_by("-budget")
        elif sort == "budget_asc":
            jobs = jobs.order_by("budget")
        else:
            jobs = jobs.order_by("-created_at")

    paginator = Paginator(jobs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {"page_obj": page_obj, "form": form}

    if request.user.is_authenticated and request.user.is_worker:
        profile = request.user.worker_profile
        applied_job_ids = set(
            profile.user.applications.values_list("job_id", flat=True)
        )
        saved_job_ids = set(SavedJob.objects.filter(worker=request.user).values_list("job_id", flat=True))
        context.update(
            {
                "profile": profile,
                "availability": request.user.availability,
                "applied_job_ids": applied_job_ids,
                "saved_job_ids": saved_job_ids,
                "checklist": {
                    "profile_photo": bool(request.user.profile_picture),
                    "skills": bool(profile.skills),
                    "verified": request.user.is_verified,
                    "bio": bool(profile.bio),
                },
            }
        )

    return render(request, "jobs/job_list.html", context)


def job_detail_view(request, pk):
    job = get_object_or_404(Job, pk=pk)
    already_applied = False
    is_saved = False
    if request.user.is_authenticated and request.user.is_worker:
        already_applied = job.applications.filter(worker=request.user).exists()
        is_saved = SavedJob.objects.filter(worker=request.user, job=job).exists()
    return render(
        request, "jobs/job_detail.html", {"job": job, "already_applied": already_applied, "is_saved": is_saved}
    )


@login_required
def toggle_save_job_view(request, pk):
    """Bookmark/unbookmark a job. Redirects back to wherever the click came from."""
    job = get_object_or_404(Job, pk=pk)
    if not request.user.is_worker:
        messages.error(request, "Only workers can save jobs.")
        return redirect("jobs:job_detail", pk=job.pk)

    saved, created = SavedJob.objects.get_or_create(worker=request.user, job=job)
    if not created:
        saved.delete()
        messages.info(request, "Removed from saved jobs.")
    else:
        messages.success(request, "Job saved.")

    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("jobs:job_detail", pk=job.pk)


@login_required
def saved_jobs_view(request):
    if not request.user.is_worker:
        messages.error(request, "Only workers have saved jobs.")
        return redirect("core:dashboard")

    saved = SavedJob.objects.filter(worker=request.user).select_related("job", "job__client", "job__category")
    applied_job_ids = set(request.user.applications.values_list("job_id", flat=True))
    return render(
        request,
        "jobs/saved_jobs.html",
        {"saved_jobs": saved, "applied_job_ids": applied_job_ids},
    )


@login_required
def job_create_view(request):
    if not request.user.is_client:
        messages.error(request, "Only clients can post jobs.")
        return redirect("core:dashboard")

    if request.method == "POST":
        form = JobForm(request.POST, request.FILES)
        if form.is_valid():
            job = form.save(commit=False)
            job.client = request.user
            job.save()
            messages.success(request, "Job posted successfully.")
            return redirect("jobs:my_job_detail", pk=job.pk)
    else:
        form = JobForm()
    return render(request, "jobs/job_create.html", {"form": form})


@login_required
def job_edit_view(request, pk):
    job = get_object_or_404(Job, pk=pk, client=request.user)
    form = JobForm(request.POST or None, request.FILES or None, instance=job)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Job updated.")
        return redirect("jobs:my_job_detail", pk=job.pk)
    return render(request, "jobs/job_edit.html", {"form": form, "job": job})


@login_required
def my_jobs_view(request):
    jobs = Job.objects.filter(client=request.user)
    return render(request, "jobs/my_jobs.html", {"jobs": jobs})


@login_required
def my_job_detail_view(request, pk):
    job = get_object_or_404(Job, pk=pk, client=request.user)
    applications = job.applications.select_related("worker")
    return render(request, "jobs/my_job_detail.html", {"job": job, "applications": applications})
