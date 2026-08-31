from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, ClientProfile, WorkerProfile, WorkerAvailability


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ["username", "email", "role", "is_verified", "is_staff"]
    list_filter = ["role", "is_verified", "is_staff"]
    fieldsets = UserAdmin.fieldsets + (
        ("Platform info", {"fields": ("role", "phone", "address", "profile_picture", "is_verified")}),
    )


admin.site.register(ClientProfile)
admin.site.register(WorkerProfile)
admin.site.register(WorkerAvailability)
