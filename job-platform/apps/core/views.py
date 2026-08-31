from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render

from apps.jobs.models import Job
from apps.applications.models import Application
from apps.contracts.models import Contract
from apps.payments.models import Payment


def home_view(request):
    latest_jobs = Job.objects.filter(status=Job.Status.OPEN)[:6]
    return render(request, "home.html", {"latest_jobs": latest_jobs})


def about_view(request):
    return render(request, "about.html")


def contact_view(request):
    return render(request, "contact.html")


@login_required
def dashboard_view(request):
    if request.user.is_client:
        return _client_dashboard(request)
    elif request.user.is_worker:
        return _worker_dashboard(request)
    return render(request, "dashboard/admin_dashboard.html")


def _client_dashboard(request):
    jobs = Job.objects.filter(client=request.user)
    active_contracts = Contract.objects.filter(client=request.user, status=Contract.Status.ACTIVE)
    total_spent = Payment.objects.filter(
        client=request.user, status=Payment.Status.SUCCESS
    ).aggregate(total=Sum("total_amount"))["total"] or 0

    context = {
        "jobs_count": jobs.count(),
        "open_jobs_count": jobs.filter(status=Job.Status.OPEN).count(),
        "active_contracts": active_contracts,
        "recent_jobs": jobs[:5],
        "total_spent": total_spent,
        "profile": request.user.client_profile,
    }
    return render(request, "dashboard/client_dashboard.html", context)


def _worker_dashboard(request):
    applications = Application.objects.filter(worker=request.user)
    active_contracts = Contract.objects.filter(worker=request.user, status=Contract.Status.ACTIVE)
    completed_contracts = Contract.objects.filter(worker=request.user, status=Contract.Status.COMPLETED)
    total_earned = Payment.objects.filter(
        contract__worker=request.user, status=Payment.Status.SUCCESS
    ).aggregate(total=Sum("worker_payout"))["total"] or 0

    profile = request.user.worker_profile
    checklist = {
        "profile_photo": bool(request.user.profile_picture),
        "skills": bool(profile.skills),
        "verified": request.user.is_verified,
        "bio": bool(profile.bio),
    }

    context = {
        "applications_count": applications.count(),
        "accepted_count": applications.filter(status=Application.Status.ACCEPTED).count(),
        "active_contracts": active_contracts,
        "completed_count": completed_contracts.count(),
        "total_earned": total_earned,
        "recent_applications": applications[:5],
        "profile": profile,
        "availability": request.user.availability,
        "checklist": checklist,
    }
    return render(request, "dashboard/worker_dashboard.html", context)
