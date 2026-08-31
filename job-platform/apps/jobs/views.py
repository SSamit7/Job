from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404

from .forms import JobForm, JobSearchForm
from .models import Job


def job_list_view(request):
    jobs = Job.objects.filter(status=Job.Status.OPEN).select_related("client", "category")
    form = JobSearchForm(request.GET or None)

    if form.is_valid():
        q = form.cleaned_data.get("q")
        location = form.cleaned_data.get("location")
        min_budget = form.cleaned_data.get("min_budget")
        max_budget = form.cleaned_data.get("max_budget")

        if q:
            jobs = jobs.filter(title__icontains=q)
        if location:
            jobs = jobs.filter(location__icontains=location)
        if min_budget:
            jobs = jobs.filter(budget__gte=min_budget)
        if max_budget:
            jobs = jobs.filter(budget__lte=max_budget)

    paginator = Paginator(jobs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {"page_obj": page_obj, "form": form}

    if request.user.is_authenticated and request.user.is_worker:
        profile = request.user.worker_profile
        applied_job_ids = set(
            profile.user.applications.values_list("job_id", flat=True)
        )
        context.update(
            {
                "profile": profile,
                "availability": request.user.availability,
                "applied_job_ids": applied_job_ids,
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
    if request.user.is_authenticated and request.user.is_worker:
        already_applied = job.applications.filter(worker=request.user).exists()
    return render(request, "jobs/job_detail.html", {"job": job, "already_applied": already_applied})


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
