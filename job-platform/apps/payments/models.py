from django.conf import settings
from django.db import models

from apps.contracts.models import Contract
from .services import calculate_split


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    class Method(models.TextChoices):
        ESEWA = "ESEWA", "eSewa"
        KHALTI = "KHALTI", "Khalti"
        BANK = "BANK", "Bank Transfer"

    contract = models.OneToOneField(Contract, on_delete=models.CASCADE, related_name="payment")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments_made")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    worker_payout = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.ESEWA)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    gateway_reference = models.CharField(
        max_length=100, blank=True, help_text="eSewa transaction_uuid or Khalti pidx - used to match the callback"
    )
    transaction_id = models.CharField(max_length=100, blank=True, help_text="The gateway's own transaction ID once paid")
    failure_reason = models.CharField(max_length=255, blank=True)
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


class WorkerWallet(models.Model):
    """
    A worker's prepaid balance. Many jobs on platforms like this get paid
    in cash directly between client and worker, so the app can't always
    skim its 10% off the transaction itself - instead the worker keeps a
    top-up balance that covers the commission, and needs at least that
    much sitting in the wallet before they're allowed to take a job.
    """

    worker = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet: {self.worker.username} - Rs. {self.balance}"

    def has_sufficient_balance(self, job_budget):
        required = calculate_split(job_budget)["platform_fee"]
        return self.balance >= required

    def credit(self, amount):
        WorkerWallet.objects.filter(pk=self.pk).update(balance=models.F("balance") + amount)
        self.refresh_from_db()

    def debit(self, amount):
        WorkerWallet.objects.filter(pk=self.pk).update(balance=models.F("balance") - amount)
        self.refresh_from_db()


class WalletTopup(models.Model):
    """
    A worker adding money to their wallet. This is a real deposit into the
    platform's own collection account (eSewa/Khalti/bank) - the worker's
    wallet balance is simply the platform's record of how much of that
    money is theirs to draw against for commission.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    class Method(models.TextChoices):
        ESEWA = "ESEWA", "eSewa"
        KHALTI = "KHALTI", "Khalti"
        BANK = "BANK", "Bank Transfer"

    worker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="topups")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.ESEWA)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    gateway_reference = models.CharField(
        max_length=100, blank=True, help_text="eSewa transaction_uuid or Khalti pidx - used to match the callback"
    )
    transaction_id = models.CharField(max_length=100, blank=True, help_text="The gateway's own transaction ID once paid")
    failure_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    credited_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Topup Rs. {self.amount} - {self.worker.username} ({self.status})"
