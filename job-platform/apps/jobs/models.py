from django.conf import settings
from django.db import models
from django.urls import reverse


class JobCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Job categories"

    def __str__(self):
        return self.name


class Job(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posted_jobs")
    category = models.ForeignKey(
        JobCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="jobs"
    )
    title = models.CharField(max_length=200)
    description = models.TextField()

    # --- Working location ---
    location = models.CharField(max_length=150, blank=True, help_text="Area / city, e.g. 'Lalitpur, Nepal'")
    address = models.CharField(
        max_length=255, blank=True, help_text="Landmark or detailed address of the work site"
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    # --- Working schedule ---
    scheduled_date = models.DateField(blank=True, null=True, help_text="Date the work should be performed")
    start_time = models.TimeField(blank=True, null=True, help_text="Time the worker should arrive")
    estimated_duration_hours = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True, help_text="Roughly how long the job takes, e.g. 2.5"
    )

    budget = models.DecimalField(max_digits=10, decimal_places=2)
    deadline = models.DateField(blank=True, null=True, help_text="Application deadline (optional)")
    image = models.ImageField(upload_to="job_images/", blank=True, null=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("jobs:job_detail", kwargs={"pk": self.pk})

    @property
    def is_open(self):
        return self.status == self.Status.OPEN

    @property
    def has_coordinates(self):
        return self.latitude is not None and self.longitude is not None

    @property
    def map_url(self):
        if self.has_coordinates:
            return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"
        if self.address or self.location:
            query = f"{self.address}, {self.location}".strip(", ")
            return f"https://www.google.com/maps/search/?api=1&query={query.replace(' ', '+')}"
        return None

    @property
    def required_commission(self):
        """The wallet balance a worker must hold to take this job."""
        from apps.payments.services import calculate_split  # local import: payments has no reverse dependency on jobs

        return calculate_split(self.budget)["platform_fee"]
