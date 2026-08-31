from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = "CLIENT", "Client"
        WORKER = "WORKER", "Worker"
        ADMIN = "ADMIN", "Admin"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.WORKER)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_client(self):
        return self.role == self.Role.CLIENT

    @property
    def is_worker(self):
        return self.role == self.Role.WORKER

    def __str__(self):
        return f"{self.username} ({self.role})"


class ClientProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="client_profile")
    company_name = models.CharField(max_length=150, blank=True)
    bio = models.TextField(blank=True)
    jobs_posted_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"ClientProfile: {self.user.username}"

    @property
    def completion_percent(self):
        checks = [
            bool(self.user.profile_picture),
            bool(self.user.phone),
            bool(self.company_name),
            bool(self.bio),
        ]
        return round(100 * sum(checks) / len(checks))


class WorkerProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="worker_profile")
    skills = models.CharField(max_length=255, blank=True, help_text="Comma-separated skills")
    bio = models.TextField(blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    resume = models.FileField(upload_to="documents/resumes/", blank=True, null=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    jobs_completed_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"WorkerProfile: {self.user.username}"

    @property
    def completion_percent(self):
        """Used to drive the profile-progress ring in the UI."""
        checks = [
            bool(self.user.profile_picture),
            bool(self.user.phone),
            bool(self.bio),
            bool(self.skills),
            bool(self.hourly_rate),
            bool(self.resume),
        ]
        return round(100 * sum(checks) / len(checks))


class WorkerAvailability(models.Model):
    """Drives the 'Your availability' widget - when a worker is open to new jobs."""

    worker = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="availability"
    )
    is_available_today = models.BooleanField(default=True)
    available_from = models.TimeField(blank=True, null=True)
    available_to = models.TimeField(blank=True, null=True)
    preferred_distance_km = models.PositiveIntegerField(default=5)
    preferred_work_types = models.CharField(
        max_length=255, blank=True, help_text="Comma-separated, e.g. Moving, Delivery, Cleaning"
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Availability: {self.worker.username}"

    @property
    def work_types_list(self):
        return [t.strip() for t in self.preferred_work_types.split(",") if t.strip()]
