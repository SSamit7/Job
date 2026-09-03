from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Kind(models.TextChoices):
        NEW_JOB = "NEW_JOB", "New job posted"
        NEW_APPLICATION = "NEW_APPLICATION", "New application"
        SELECTED = "SELECTED", "Selected for a job"
        PAYMENT_SUCCESS = "PAYMENT_SUCCESS", "Payment received"
        WALLET_TOPUP = "WALLET_TOPUP", "Wallet topped up"
        GENERAL = "GENERAL", "General"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.GENERAL)
    message = models.CharField(max_length=255)
    link = models.CharField(max_length=255, blank=True, help_text="Relative URL to open when clicked")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"To {self.recipient.username}: {self.message}"
