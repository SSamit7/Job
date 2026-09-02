from urllib.parse import quote

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from apps.contracts.models import Contract
from .forms import TopupAmountForm
from .gateways import (
    esewa_payment_fields,
    esewa_decode_callback,
    esewa_verify_callback,
    esewa_check_status,
    khalti_initiate,
    khalti_lookup,
    KhaltiError,
    KhaltiNotConfigured,
)
from .models import Payment, PlatformWallet, CommissionLedgerEntry, WorkerWallet, WalletTopup
from .services import calculate_split, credit_commission, credit_topup


# ==========================================================================
# Job payments (client pays worker, platform takes 10% commission)
# ==========================================================================

@login_required
def initiate_payment_view(request, contract_pk):
    """The checkout landing page: order summary + choice of payment method."""
    contract = get_object_or_404(
        Contract, pk=contract_pk, client=request.user, status=Contract.Status.COMPLETED
    )
    payment, _ = Payment.objects.get_or_create(
        contract=contract,
        defaults={"client": request.user, "total_amount": contract.agreed_amount},
    )
    if payment.status == Payment.Status.SUCCESS:
        return redirect("payments:payment_success", pk=payment.pk)

    split = calculate_split(contract.agreed_amount)
    return render(request, "payments/payment.html", {"contract": contract, "payment": payment, "split": split})


@login_required
def start_payment_view(request, contract_pk, method):
    """Client picked a method on the checkout page -> kick off the real gateway."""
    contract = get_object_or_404(Contract, pk=contract_pk, client=request.user, status=Contract.Status.COMPLETED)
    payment = get_object_or_404(Payment, contract=contract)

    if method not in Payment.Method.values:
        messages.error(request, "Unknown payment method.")
        return redirect("payments:initiate_payment", contract_pk=contract.pk)

    if payment.status == Payment.Status.SUCCESS:
        return redirect("payments:payment_success", pk=payment.pk)

    payment.method = method
    payment.status = Payment.Status.PENDING
    payment.gateway_reference = f"PAY-{payment.pk}"
    payment.save(update_fields=["method", "status", "gateway_reference"])

    if method == Payment.Method.ESEWA:
        success_url = settings.SITE_BASE_URL + reverse("payments:esewa_payment_callback")
        failure_url = (
            settings.SITE_BASE_URL
            + reverse("payments:esewa_payment_failure")
            + f"?ref={payment.gateway_reference}"
        )
        fields = esewa_payment_fields(payment.total_amount, payment.gateway_reference, success_url, failure_url)
        return render(
            request,
            "payments/esewa_redirect.html",
            {"fields": fields, "esewa_url": settings.ESEWA_PAYMENT_URL, "amount": payment.total_amount},
        )

    if method == Payment.Method.KHALTI:
        return_url = settings.SITE_BASE_URL + reverse("payments:khalti_payment_callback")
        customer = {
            "name": contract.client.username,
            "email": contract.client.email,
            "phone": contract.client.phone,
        }
        try:
            pidx, payment_url = khalti_initiate(
                payment.total_amount, payment.gateway_reference, f"Payment for {contract.job.title}", customer, return_url
            )
        except KhaltiNotConfigured as exc:
            messages.error(request, str(exc))
            return redirect("payments:initiate_payment", contract_pk=contract.pk)
        except KhaltiError:
            payment.status = Payment.Status.FAILED
            payment.failure_reason = "Khalti couldn't start this payment"
            payment.save()
            messages.error(request, "Khalti couldn't start this payment. Please try again.")
            return redirect("payments:initiate_payment", contract_pk=contract.pk)

        payment.gateway_reference = pidx
        payment.save(update_fields=["gateway_reference"])
        return redirect(payment_url)

    # BANK
    return redirect("payments:bank_payment", pk=payment.pk)


@login_required
def esewa_payment_callback_view(request):
    """eSewa redirects the client's browser back here after a job payment."""
    data_param = request.GET.get("data", "")
    try:
        payload = esewa_decode_callback(data_param)
    except (ValueError, TypeError):
        messages.error(request, "Couldn't read eSewa's response. If money was deducted, contact support.")
        return redirect("core:dashboard")

    if not esewa_verify_callback(payload):
        messages.error(request, "eSewa's response failed signature verification - treating this as not paid, for safety.")
        return redirect("core:dashboard")

    transaction_uuid = payload.get("transaction_uuid")
    payment = Payment.objects.filter(gateway_reference=transaction_uuid, client=request.user).first()
    if not payment:
        messages.error(request, "Couldn't match this payment to a contract.")
        return redirect("core:dashboard")

    if payment.status == Payment.Status.SUCCESS:
        return redirect("payments:payment_success", pk=payment.pk)

    # Defense in depth: don't just trust the redirect, ask eSewa directly too.
    status_data = esewa_check_status(transaction_uuid, payment.total_amount)

    if payload.get("status") == "COMPLETE" and status_data.get("status") == "COMPLETE":
        payment.transaction_id = payload.get("transaction_code", "")
        payment.status = Payment.Status.SUCCESS
        payment.paid_at = timezone.now()
        payment.save()
        credit_commission(payment)
        messages.success(request, "Payment successful. 10% commission credited to the platform, 90% released to the worker.")
        return redirect("payments:payment_success", pk=payment.pk)

    payment.status = Payment.Status.FAILED
    payment.failure_reason = f"eSewa status: {payload.get('status')}"
    payment.save()
    return redirect("payments:payment_failed", pk=payment.pk)


@login_required
def esewa_payment_failure_view(request):
    """eSewa's failure_url - also hit if the client cancels at eSewa."""
    ref = request.GET.get("ref")
    payment = None
    if ref:
        payment = Payment.objects.filter(
            gateway_reference=ref, client=request.user, status=Payment.Status.PENDING
        ).first()
        if payment:
            payment.status = Payment.Status.CANCELLED
            payment.failure_reason = "Cancelled or failed at eSewa"
            payment.save()
    messages.warning(request, "Payment was cancelled or didn't complete. Nothing was charged.")
    if payment:
        return redirect("payments:payment_failed", pk=payment.pk)
    return redirect("core:dashboard")


@login_required
def khalti_payment_callback_view(request):
    """Khalti's return_url - GET with pidx/status query params."""
    pidx = request.GET.get("pidx")
    if not pidx:
        messages.error(request, "Missing payment reference from Khalti.")
        return redirect("core:dashboard")

    payment = Payment.objects.filter(gateway_reference=pidx, client=request.user).first()
    if not payment:
        messages.error(request, "Couldn't match this payment to a contract.")
        return redirect("core:dashboard")

    if payment.status == Payment.Status.SUCCESS:
        return redirect("payments:payment_success", pk=payment.pk)

    try:
        # Khalti's own docs: always confirm via lookup, don't trust the redirect alone.
        lookup = khalti_lookup(pidx)
    except (requests.RequestException, ValueError):
        messages.error(request, "Couldn't verify this payment with Khalti. Please contact support before retrying.")
        return redirect("payments:payment_detail", pk=payment.pk)

    if lookup.get("status") == "Completed":
        payment.transaction_id = lookup.get("transaction_id", "")
        payment.status = Payment.Status.SUCCESS
        payment.paid_at = timezone.now()
        payment.save()
        credit_commission(payment)
        messages.success(request, "Payment successful. 10% commission credited to the platform, 90% released to the worker.")
        return redirect("payments:payment_success", pk=payment.pk)

    payment.status = (
        Payment.Status.CANCELLED if lookup.get("status") == "User canceled" else Payment.Status.FAILED
    )
    payment.failure_reason = f"Khalti status: {lookup.get('status')}"
    payment.save()
    return redirect("payments:payment_failed", pk=payment.pk)


@login_required
def bank_payment_view(request, pk):
    """
    Bank transfer has no gateway to verify against automatically, so it stays
    PENDING until an admin approves it (see PaymentAdmin.approve_and_credit).
    """
    payment = get_object_or_404(Payment, pk=pk, client=request.user, method=Payment.Method.BANK)

    qr_payload = (
        f"Account Name: JobPlatform Pvt Ltd|Account No: 0123456789012"
        f"|Bank: Nepal Investment Bank|Amount: Rs.{payment.total_amount}|Reference: PAY-{payment.pk}"
    )
    qr_image_url = "https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=" + quote(qr_payload)

    if request.method == "POST" and payment.status == Payment.Status.PENDING:
        messages.success(
            request,
            "Thanks - we'll confirm your transfer and release payment to the worker shortly. "
            "This is manual, so it isn't instant like eSewa/Khalti.",
        )
        return redirect("contracts:contract_detail", pk=payment.contract.pk)

    return render(request, "payments/bank_payment.html", {"payment": payment, "qr_image_url": qr_image_url})


@login_required
def payment_success_view(request, pk):
    payment = get_object_or_404(Payment, pk=pk, status=Payment.Status.SUCCESS)
    if request.user not in (payment.client, payment.contract.worker):
        messages.error(request, "You don't have access to that payment.")
        return redirect("core:dashboard")
    return render(request, "payments/payment_success.html", {"payment": payment})


@login_required
def payment_failed_view(request, pk):
    payment = get_object_or_404(Payment, pk=pk, client=request.user)
    return render(request, "payments/payment_failed.html", {"payment": payment})


@login_required
def payment_detail_view(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if request.user not in (payment.client, payment.contract.worker) and not request.user.is_staff:
        messages.error(request, "You don't have access to that payment.")
        return redirect("core:dashboard")
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


# ==========================================================================
# Worker wallet top-ups
# ==========================================================================

@login_required
def wallet_view(request):
    """A worker's own wallet: balance, top-up options, and top-up history."""
    if not request.user.is_worker:
        messages.error(request, "Wallets are for workers only.")
        return redirect("core:dashboard")

    wallet, _ = WorkerWallet.objects.get_or_create(worker=request.user)
    topups = WalletTopup.objects.filter(worker=request.user)[:20]

    return render(
        request,
        "payments/wallet.html",
        {"wallet": wallet, "topups": topups, "methods": WalletTopup.Method.choices},
    )


@login_required
def initiate_topup_view(request, method):
    """Step 2: worker picked a top-up method and entered an amount -> kick off the real gateway."""
    if not request.user.is_worker:
        messages.error(request, "Wallets are for workers only.")
        return redirect("core:dashboard")

    if method not in WalletTopup.Method.values:
        messages.error(request, "Unknown top-up method.")
        return redirect("payments:wallet")

    form = TopupAmountForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        topup = form.save(commit=False)
        topup.worker = request.user
        topup.method = method
        topup.save()
        topup.gateway_reference = f"TOPUP-{topup.pk}"
        topup.save(update_fields=["gateway_reference"])

        if method == WalletTopup.Method.ESEWA:
            success_url = settings.SITE_BASE_URL + reverse("payments:esewa_callback")
            failure_url = (
                settings.SITE_BASE_URL + reverse("payments:esewa_failure") + f"?ref={topup.gateway_reference}"
            )
            fields = esewa_payment_fields(topup.amount, topup.gateway_reference, success_url, failure_url)
            return render(
                request,
                "payments/esewa_redirect.html",
                {"fields": fields, "esewa_url": settings.ESEWA_PAYMENT_URL, "amount": topup.amount},
            )

        if method == WalletTopup.Method.KHALTI:
            return_url = settings.SITE_BASE_URL + reverse("payments:khalti_callback")
            customer = {"name": request.user.username, "email": request.user.email, "phone": request.user.phone}
            try:
                pidx, payment_url = khalti_initiate(
                    topup.amount, topup.gateway_reference, "JobPlatform wallet top-up", customer, return_url
                )
            except KhaltiNotConfigured as exc:
                topup.delete()  # never happened - don't leave a dead PENDING row behind
                messages.error(request, str(exc))
                return redirect("payments:wallet")
            except KhaltiError:
                topup.status = WalletTopup.Status.FAILED
                topup.failure_reason = "Khalti couldn't start this payment"
                topup.save()
                messages.error(request, "Khalti couldn't start this payment. Please try again.")
                return redirect("payments:wallet")

            topup.gateway_reference = pidx
            topup.save(update_fields=["gateway_reference"])
            return redirect(payment_url)

        if method == WalletTopup.Method.BANK:
            return redirect("payments:bank_topup", pk=topup.pk)

    return render(
        request,
        "payments/topup_amount.html",
        {"form": form, "method": method, "method_label": dict(WalletTopup.Method.choices)[method]},
    )


@login_required
def esewa_callback_view(request):
    """eSewa redirects the user's browser back here (GET, base64 `data` param) after payment."""
    data_param = request.GET.get("data", "")
    try:
        payload = esewa_decode_callback(data_param)
    except (ValueError, TypeError):
        messages.error(request, "Couldn't read eSewa's response. If money was deducted, contact support.")
        return redirect("payments:wallet")

    if not esewa_verify_callback(payload):
        messages.error(request, "eSewa's response failed signature verification - treating this as not paid, for safety.")
        return redirect("payments:wallet")

    transaction_uuid = payload.get("transaction_uuid")
    topup = WalletTopup.objects.filter(gateway_reference=transaction_uuid, worker=request.user).first()
    if not topup:
        messages.error(request, "Couldn't match this payment to a top-up request.")
        return redirect("payments:wallet")

    if topup.status == WalletTopup.Status.SUCCESS:
        return redirect("payments:wallet")  # already credited - don't process twice

    # Defense in depth: don't just trust the redirect, ask eSewa directly too.
    status_data = esewa_check_status(transaction_uuid, topup.amount)

    if payload.get("status") == "COMPLETE" and status_data.get("status") == "COMPLETE":
        topup.transaction_id = payload.get("transaction_code", "")
        topup.status = WalletTopup.Status.SUCCESS
        topup.save()
        credit_topup(topup)  # sets credited_at and actually moves the balance
        messages.success(request, f"Rs. {topup.amount} added to your wallet. You're ready to apply for jobs.")
        return redirect("jobs:job_list")

    topup.status = WalletTopup.Status.FAILED
    topup.failure_reason = f"eSewa status: {payload.get('status')}"
    topup.save()
    messages.error(request, "eSewa reported this payment did not complete. No amount was added.")
    return redirect("payments:wallet")


@login_required
def esewa_failure_view(request):
    """eSewa's failure_url - also hit if the user cancels at eSewa."""
    ref = request.GET.get("ref")
    if ref:
        topup = WalletTopup.objects.filter(
            gateway_reference=ref, worker=request.user, status=WalletTopup.Status.PENDING
        ).first()
        if topup:
            topup.status = WalletTopup.Status.CANCELLED
            topup.failure_reason = "Cancelled or failed at eSewa"
            topup.save()
    messages.warning(request, "Payment was cancelled or didn't complete. No amount was added to your wallet.")
    return redirect("payments:wallet")


@login_required
def khalti_callback_view(request):
    """Khalti's return_url - GET with pidx/status query params."""
    pidx = request.GET.get("pidx")
    if not pidx:
        messages.error(request, "Missing payment reference from Khalti.")
        return redirect("payments:wallet")

    topup = WalletTopup.objects.filter(gateway_reference=pidx, worker=request.user).first()
    if not topup:
        messages.error(request, "Couldn't match this payment to a top-up request.")
        return redirect("payments:wallet")

    if topup.status == WalletTopup.Status.SUCCESS:
        return redirect("payments:wallet")  # already credited - don't process twice

    try:
        # Khalti's own docs: always confirm via lookup, don't trust the redirect alone.
        lookup = khalti_lookup(pidx)
    except (requests.RequestException, ValueError):
        messages.error(request, "Couldn't verify this payment with Khalti. Please contact support before retrying.")
        return redirect("payments:wallet")

    if lookup.get("status") == "Completed":
        topup.transaction_id = lookup.get("transaction_id", "")
        topup.status = WalletTopup.Status.SUCCESS
        topup.save()
        credit_topup(topup)
        messages.success(request, f"Rs. {topup.amount} added to your wallet. You're ready to apply for jobs.")
        return redirect("jobs:job_list")

    topup.status = (
        WalletTopup.Status.CANCELLED if lookup.get("status") == "User canceled" else WalletTopup.Status.FAILED
    )
    topup.failure_reason = f"Khalti status: {lookup.get('status')}"
    topup.save()
    messages.warning(request, f"Khalti payment {lookup.get('status', 'did not complete').lower()}. No amount was added.")
    return redirect("payments:wallet")


@login_required
def bank_topup_view(request, pk):
    """
    Bank transfer has no gateway to verify against automatically, so it stays
    PENDING until an admin approves it (see WalletTopupAdmin.approve_and_credit).
    """
    topup = get_object_or_404(WalletTopup, pk=pk, worker=request.user, method=WalletTopup.Method.BANK)

    qr_payload = (
        f"Account Name: JobPlatform Pvt Ltd|Account No: 0123456789012"
        f"|Bank: Nepal Investment Bank|Amount: Rs.{topup.amount}|Reference: TOPUP-{topup.pk}"
    )
    qr_image_url = "https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=" + quote(qr_payload)

    if request.method == "POST" and topup.status == WalletTopup.Status.PENDING:
        messages.success(
            request,
            "Thanks - we'll confirm your transfer and credit your wallet shortly. "
            "This is manual, so it isn't instant like eSewa/Khalti.",
        )
        return redirect("payments:wallet")

    return render(request, "payments/bank_topup.html", {"topup": topup, "qr_image_url": qr_image_url})
