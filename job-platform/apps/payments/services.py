"""
Central place for all commission-splitting math.
Never hardcode `* 0.9` or `* 0.1` anywhere else in the codebase -
always call calculate_split() so the rate stays configurable in one spot.
"""
from decimal import Decimal, ROUND_HALF_UP
from django.utils.timezone import now as timezone_now

PLATFORM_COMMISSION_RATE = Decimal("0.10")  # 10% held by the platform


def calculate_split(total_amount) -> dict:
    """
    Given the total agreed job amount, return the platform's commission
    and the worker's payout.
    """
    total_amount = Decimal(str(total_amount))
    platform_fee = (total_amount * PLATFORM_COMMISSION_RATE).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    worker_payout = total_amount - platform_fee

    return {
        "total": total_amount,
        "platform_fee": platform_fee,
        "worker_payout": worker_payout,
    }


def credit_commission(payment):
    """
    Move a successful payment's platform_fee into the admin's wallet balance
    and log it in the ledger. Called once, right when a payment succeeds -
    no token purchase or manual payout step needed on either side.
    Safe to call more than once: a payment can only ever be credited once.
    """
    from .models import PlatformWallet, CommissionLedgerEntry  # local import: avoids circular import with models.py

    if CommissionLedgerEntry.objects.filter(payment=payment).exists():
        return

    CommissionLedgerEntry.objects.create(payment=payment, amount=payment.platform_fee)
    PlatformWallet.get_instance().credit(payment.platform_fee)

    _notify_payment_success(payment)


def required_commission_for(job):
    """The wallet balance a worker must hold before they can take this job."""
    return calculate_split(job.budget)["platform_fee"]


def credit_topup(topup):
    """
    Called once a top-up 'lands' in the platform's collection account.
    Credits the worker's internal wallet ledger by the same amount.
    Idempotency is based solely on `credited_at` - the caller should NOT
    set that field itself before calling this, or it will look like it's
    already been credited and the balance will never actually move.
    """
    from .models import WorkerWallet

    if topup.credited_at:
        return  # already credited - never double-credit a retried call

    wallet, _ = WorkerWallet.objects.get_or_create(worker=topup.worker)
    wallet.credit(topup.amount)

    topup.credited_at = timezone_now()
    topup.save(update_fields=["credited_at"])

    _notify_topup_success(topup)


def _notify_payment_success(payment):
    from apps.notifications.models import Notification
    from apps.notifications.services import notify

    job_title = payment.contract.job.title
    notify(
        payment.contract.worker,
        f'Payment received for "{job_title}" - Rs. {payment.worker_payout} added to your earnings.',
        kind=Notification.Kind.PAYMENT_SUCCESS,
        link=f"/contracts/{payment.contract.pk}/",
    )
    notify(
        payment.client,
        f'Your payment for "{job_title}" went through - contact details are now visible.',
        kind=Notification.Kind.PAYMENT_SUCCESS,
        link=f"/contracts/{payment.contract.pk}/",
    )


def _notify_topup_success(topup):
    from apps.notifications.models import Notification
    from apps.notifications.services import notify

    notify(
        topup.worker,
        f"Rs. {topup.amount} added to your wallet via {topup.get_method_display()}.",
        kind=Notification.Kind.WALLET_TOPUP,
        link="/payments/wallet/",
    )
