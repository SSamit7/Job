import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from apps.contracts.models import Contract
from .forms import TopupForm
from .models import Payment, PlatformWallet, CommissionLedgerEntry, WorkerWallet, WalletTopup
from .services import calculate_split, credit_commission, credit_topup


@login_required
def initiate_payment_view(request, contract_pk):
    contract = get_object_or_404(
        Contract, pk=contract_pk, client=request.user, status=Contract.Status.COMPLETED
    )
    payment, _ = Payment.objects.get_or_create(
        contract=contract,
        defaults={"client": request.user, "total_amount": contract.agreed_amount},
    )
    split = calculate_split(contract.agreed_amount)
    return render(request, "payments/payment.html", {"contract": contract, "payment": payment, "split": split})


@login_required
def process_payment_view(request, contract_pk):
    """
    Simulated payment gateway callback. Swap the body of this view for a real
    gateway integration (eSewa / Khalti / Stripe) - the commission split
    logic in services.py stays exactly the same either way.
    """
    contract = get_object_or_404(Contract, pk=contract_pk, client=request.user)
    payment = get_object_or_404(Payment, contract=contract)

    if request.method == "POST":
        payment.method = request.POST.get("method", Payment.Method.CARD)
        payment.transaction_id = str(uuid.uuid4())
        payment.status = Payment.Status.SUCCESS
        payment.paid_at = timezone.now()
        payment.save()
        credit_commission(payment)
        messages.success(request, "Payment successful. 10% commission held by platform, 90% released to worker.")
        return redirect("payments:payment_success", pk=payment.pk)

    return redirect("payments:initiate_payment", contract_pk=contract.pk)


@login_required
def payment_success_view(request, pk):
    payment = get_object_or_404(Payment, pk=pk, status=Payment.Status.SUCCESS)
    return render(request, "payments/payment_success.html", {"payment": payment})


@login_required
def payment_failed_view(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    return render(request, "payments/payment_failed.html", {"payment": payment})


@login_required
def payment_detail_view(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    return render(request, "payments/payment_detail.html", {"payment": payment})


@login_required
def transaction_history_view(request):
    if request.user.is_client:
        payments = Payment.objects.filter(client=request.user)
    else:
        payments = Payment.objects.filter(contract__worker=request.user)
    return render(request, "payments/transaction_history.html", {"payments": payments})


@login_required
def platform_wallet_view(request):
    """Admin-only: shows the running commission balance and its audit trail."""
    if not request.user.is_staff:
        messages.error(request, "That page is for platform admins only.")
        return redirect("core:dashboard")

    wallet = PlatformWallet.get_instance()
    entries = CommissionLedgerEntry.objects.select_related(
        "payment", "payment__contract", "payment__contract__job"
    )[:100]
    return render(request, "payments/platform_wallet.html", {"wallet": wallet, "entries": entries})


@login_required
def wallet_view(request):
    """A worker's own wallet: balance, top-up form, and top-up history."""
    if not request.user.is_worker:
        messages.error(request, "Wallets are for workers only.")
        return redirect("core:dashboard")

    wallet, _ = WorkerWallet.objects.get_or_create(worker=request.user)
    form = TopupForm()
    topups = WalletTopup.objects.filter(worker=request.user)[:20]

    return render(request, "payments/wallet.html", {"wallet": wallet, "form": form, "topups": topups})


@login_required
def initiate_topup_view(request):
    if not request.user.is_worker:
        messages.error(request, "Wallets are for workers only.")
        return redirect("core:dashboard")

    form = TopupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        topup = form.save(commit=False)
        topup.worker = request.user
        topup.save()
        return redirect("payments:process_topup", pk=topup.pk)

    wallet, _ = WorkerWallet.objects.get_or_create(worker=request.user)
    topups = WalletTopup.objects.filter(worker=request.user)[:20]
    messages.error(request, "Please fix the errors below.")
    return render(request, "payments/wallet.html", {"wallet": wallet, "form": form, "topups": topups})


@login_required
def process_topup_view(request, pk):
    """
    Simulated deposit-gateway callback, same pattern as process_payment_view.
    Swap the body for a real eSewa/Khalti/bank webhook - credit_topup()
    (the actual wallet-crediting logic) stays exactly the same either way.
    """
    topup = get_object_or_404(WalletTopup, pk=pk, worker=request.user)

    if topup.status != WalletTopup.Status.SUCCESS:
        topup.transaction_id = str(uuid.uuid4())
        topup.status = WalletTopup.Status.SUCCESS
        topup.credited_at = timezone.now()
        topup.save()
        credit_topup(topup)
        messages.success(request, f"Rs. {topup.amount} added to your wallet.")

    return redirect("payments:wallet")
