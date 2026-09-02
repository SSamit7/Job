from django.contrib import admin
from django.utils import timezone
from .models import Payment, PlatformWallet, CommissionLedgerEntry, WorkerWallet, WalletTopup
from .services import credit_topup, credit_commission


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "contract", "total_amount", "platform_fee", "worker_payout", "status", "method", "gateway_reference"]
    list_filter = ["status", "method"]
    readonly_fields = ["platform_fee", "worker_payout"]
    actions = ["approve_and_credit"]

    @admin.action(description="Approve selected PENDING bank transfers, release payment and credit commission")
    def approve_and_credit(self, request, queryset):
        approved = 0
        for payment in queryset.filter(status=Payment.Status.PENDING, method=Payment.Method.BANK):
            payment.status = Payment.Status.SUCCESS
            payment.paid_at = timezone.now()
            payment.save()
            credit_commission(payment)
            approved += 1
        self.message_user(request, f"Approved and released {approved} bank payment(s).")


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
    list_display = ["id", "worker", "amount", "method", "status", "gateway_reference", "created_at"]
    list_filter = ["status", "method"]
    readonly_fields = ["credited_at"]
    actions = ["approve_and_credit"]

    @admin.action(description="Approve selected PENDING bank transfers and credit wallet")
    def approve_and_credit(self, request, queryset):
        approved = 0
        for topup in queryset.filter(status=WalletTopup.Status.PENDING, method=WalletTopup.Method.BANK):
            topup.status = WalletTopup.Status.SUCCESS
            topup.save()
            credit_topup(topup)
            approved += 1
        self.message_user(request, f"Approved and credited {approved} bank transfer(s).")
