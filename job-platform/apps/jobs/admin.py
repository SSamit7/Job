from django.contrib import admin
from .models import Job, JobCategory, SavedJob

admin.site.register(JobCategory)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ["title", "client", "budget", "status", "created_at"]
    list_filter = ["status", "category"]
    search_fields = ["title", "description"]


@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ["worker", "job", "saved_at"]
