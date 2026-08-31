"""
Central place for all commission-splitting math.
Never hardcode `* 0.9` or `* 0.1` anywhere else in the codebase -
always call calculate_split() so the rate stays configurable in one spot.
"""
from decimal import Decimal, ROUND_HALF_UP

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
