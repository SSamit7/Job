from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from apps.jobs.models import Job
from .models import Contract


@login_required
def contract_list_view(request):
    if request.user.is_client:
        contracts = Contract.objects.filter(client=request.user)
    else:
        contracts = Contract.objects.filter(worker=request.user)
    return render(request, "contracts/contract_list.html", {"contracts": contracts})


@login_required
def contract_detail_view(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    return render(request, "contracts/contract_detail.html", {"contract": contract})


@login_required
def mark_job_completed_view(request, pk):
    """Client confirms the work is done -> job flips to COMPLETED, ready for payment."""
    contract = get_object_or_404(Contract, pk=pk, client=request.user, status=Contract.Status.ACTIVE)

    contract.status = Contract.Status.COMPLETED
    contract.completed_at = timezone.now()
    contract.save()

    contract.job.status = Job.Status.COMPLETED
    contract.job.save()

    messages.success(request, "Job marked as completed. You can now proceed to payment.")
    return redirect("payments:initiate_payment", contract_pk=contract.pk)
