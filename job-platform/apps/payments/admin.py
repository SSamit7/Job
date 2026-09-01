from django.contrib import admin
from .models import Payment, PlatformWallet, CommissionLedgerEntry, WorkerWallet, WalletTopup


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "contract", "total_amount", "platform_fee", "worker_payout", "status", "method"]
    list_filter = ["status", "method"]
    readonly_fields = ["platform_fee", "worker_payout"]


@admin.register(PlatformWallet)
class PlatformWalletAdmin(admin.ModelAdmin):
    list_display = ["balance", "updated_at"]

    def has_add_permission(self, request):
        # Singleton - never create a second wallet row from the admin.
        return not PlatformWallet.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CommissionLedgerEntry)
class CommissionLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ["id", "payment", "amount", "created_at"]
    readonly_fields = ["payment", "amount", "created_at"]

    def has_add_permission(self, request):
        # Entries are only ever created by credit_commission(), never by hand.
        return False


@admin.register(WorkerWallet)
class WorkerWalletAdmin(admin.ModelAdmin):
    list_display = ["worker", "balance", "updated_at"]
    search_fields = ["worker__username"]


@admin.register(WalletTopup)
class WalletTopupAdmin(admin.ModelAdmin):
    list_display = ["id", "worker", "amount", "method", "status", "created_at"]
    list_filter = ["status", "method"]
