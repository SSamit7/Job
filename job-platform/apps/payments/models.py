from django.conf import settings
from django.db import models

from apps.contracts.models import Contract
from .services import calculate_split


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    class Method(models.TextChoices):
        CARD = "CARD", "Card"
        ESEWA = "ESEWA", "eSewa"
        KHALTI = "KHALTI", "Khalti"
        BANK = "BANK", "Bank Transfer"

    contract = models.OneToOneField(Contract, on_delete=models.CASCADE, related_name="payment")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments_made")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    worker_payout = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.CARD)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    transaction_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.platform_fee is None or self.worker_payout is None:
            split = calculate_split(self.total_amount)
            self.platform_fee = split["platform_fee"]
            self.worker_payout = split["worker_payout"]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payment #{self.pk} - {self.status}"


class PlatformWallet(models.Model):
    """
    Singleton row = the admin/platform's commission balance.
    There is only ever one row (pk=1). No token or credit purchase is
    involved anywhere in this flow - the wallet is credited automatically
    out of each successful payment's 10% commission, the same way
    Pathao/Uber-style platforms take their cut at the moment of payment.
    """

    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Platform wallet"
        verbose_name_plural = "Platform wallet"

    def __str__(self):
        return f"Platform Wallet - Rs. {self.balance}"

    @classmethod
    def get_instance(cls):
        wallet, _ = cls.objects.get_or_create(pk=1)
        return wallet

    def credit(self, amount):
        """Atomically add `amount` to the balance."""
        PlatformWallet.objects.filter(pk=self.pk).update(balance=models.F("balance") + amount)
        self.refresh_from_db()


class CommissionLedgerEntry(models.Model):
    """One audit row per commission credited to the platform wallet."""

    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name="ledger_entry")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Commission Rs. {self.amount} from Payment #{self.payment_id}"
