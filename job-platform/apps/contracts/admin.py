from django.contrib import admin
from .models import Contract


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ["id", "job", "client", "worker", "agreed_amount", "status"]
    list_filter = ["status"]
