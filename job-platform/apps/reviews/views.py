from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.shortcuts import render, redirect, get_object_or_404

from apps.contracts.models import Contract
from apps.accounts.models import WorkerProfile
from .forms import ReviewForm
from .models import Review


@login_required
def create_review_view(request, contract_pk):
    contract = get_object_or_404(Contract, pk=contract_pk, status=Contract.Status.COMPLETED)

    if request.user not in (contract.client, contract.worker):
        messages.error(request, "You are not part of this contract.")
        return redirect("core:dashboard")

    reviewee = contract.worker if request.user == contract.client else contract.client

    if Review.objects.filter(contract=contract, reviewer=request.user).exists():
        messages.warning(request, "You already reviewed this contract.")
        return redirect("contracts:contract_detail", pk=contract.pk)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.contract = contract
            review.reviewer = request.user
            review.reviewee = reviewee
            review.save()

            if reviewee.is_worker:
                avg = Review.objects.filter(reviewee=reviewee).aggregate(avg=Avg("rating"))["avg"]
                WorkerProfile.objects.filter(user=reviewee).update(average_rating=round(avg, 2))

            messages.success(request, "Review submitted.")
            return redirect("contracts:contract_detail", pk=contract.pk)
    else:
        form = ReviewForm()

    return render(
        request, "reviews/create_review.html", {"form": form, "contract": contract, "reviewee": reviewee}
    )


def review_list_view(request, user_pk):
    reviews = Review.objects.filter(reviewee__pk=user_pk).select_related("reviewer")
    return render(request, "reviews/review_list.html", {"reviews": reviews})
