from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from apps.jobs.models import Job
from apps.contracts.models import Contract
from apps.payments.models import WorkerWallet
from apps.payments.services import required_commission_for
from .forms import ApplicationForm
from .models import Application


@login_required
def apply_job_view(request, job_pk):
    job = get_object_or_404(Job, pk=job_pk, status=Job.Status.OPEN)

    if not request.user.is_worker:
        messages.error(request, "Only workers can apply for jobs.")
        return redirect("jobs:job_detail", pk=job.pk)

    if Application.objects.filter(job=job, worker=request.user).exists():
        messages.warning(request, "You already applied for this job.")
        return redirect("jobs:job_detail", pk=job.pk)

    wallet, _ = WorkerWallet.objects.get_or_create(worker=request.user)
    required = required_commission_for(job)
    if wallet.balance < required:
        messages.error(
            request,
            f"You need at least Rs. {required} in your wallet (the platform's 10% commission on this "
            f"job) before you can take it. Your current balance is Rs. {wallet.balance}.",
        )
        return redirect("payments:wallet")

    if request.method == "POST":
        form = ApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.worker = request.user
            application.save()
            messages.success(request, "Application submitted.")
            return redirect("applications:my_applications")
    else:
        form = ApplicationForm()

    return render(
        request,
        "applications/application_form.html",
        {"form": form, "job": job, "required_commission": required, "wallet": wallet},
    )


@login_required
def application_detail_view(request, pk):
    application = get_object_or_404(Application, pk=pk)
    return render(request, "applications/application_detail.html", {"application": application})


@login_required
def my_applications_view(request):
    applications = Application.objects.filter(worker=request.user).select_related("job")
    return render(request, "applications/my_applications.html", {"applications": applications})


@login_required
def received_applications_view(request):
    applications = Application.objects.filter(job__client=request.user).select_related("job", "worker")
    return render(request, "applications/received_applications.html", {"applications": applications})


@login_required
def select_worker_view(request, pk):
    """Client picks a worker for their job -> creates the Contract (matches the diagram's CONTRACT step)."""
    application = get_object_or_404(Application, pk=pk, job__client=request.user)
    job = application.job

    if job.status != Job.Status.OPEN:
        messages.error(request, "This job is no longer open.")
        return redirect("jobs:my_job_detail", pk=job.pk)

    wallet, _ = WorkerWallet.objects.get_or_create(worker=application.worker)
    required = required_commission_for(job)
    if wallet.balance < required:
        messages.error(
            request,
            f"{application.worker.username}'s wallet balance dropped below the required commission "
            f"(Rs. {required}) since they applied, so they can't be selected right now. Ask them to top "
            f"up, or choose a different applicant.",
        )
        return redirect("jobs:my_job_detail", pk=job.pk)

    application.status = Application.Status.ACCEPTED
    application.save()

    job.applications.exclude(pk=application.pk).update(status=Application.Status.REJECTED)
    job.status = Job.Status.IN_PROGRESS
    job.save()

    Contract.objects.get_or_create(
        job=job,
        application=application,
        defaults={
            "client": job.client,
            "worker": application.worker,
            "agreed_amount": application.proposed_amount or job.budget,
        },
    )

    messages.success(request, f"{application.worker.username} selected. Contract created.")
    return redirect("jobs:my_job_detail", pk=job.pk)
