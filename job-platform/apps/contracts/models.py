from django.conf import settings
from django.db import models

from apps.jobs.models import Job
from apps.applications.models import Application


class Contract(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name="contract")
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name="contract")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="client_contracts")
    worker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="worker_contracts")
    agreed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Contract #{self.pk} - {self.job.title}"
