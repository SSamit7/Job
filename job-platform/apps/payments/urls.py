from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    # Job payments (client -> worker, 10% commission)
    path("contract/<int:contract_pk>/pay/", views.initiate_payment_view, name="initiate_payment"),
    path("contract/<int:contract_pk>/pay/<str:method>/", views.start_payment_view, name="start_payment"),
    path("job-payment/esewa/callback/", views.esewa_payment_callback_view, name="esewa_payment_callback"),
    path("job-payment/esewa/failure/", views.esewa_payment_failure_view, name="esewa_payment_failure"),
    path("job-payment/khalti/callback/", views.khalti_payment_callback_view, name="khalti_payment_callback"),
    path("job-payment/<int:pk>/bank/", views.bank_payment_view, name="bank_payment"),
    path("success/<int:pk>/", views.payment_success_view, name="payment_success"),
    path("failed/<int:pk>/", views.payment_failed_view, name="payment_failed"),
    path("history/", views.transaction_history_view, name="transaction_history"),
    path("platform-wallet/", views.platform_wallet_view, name="platform_wallet"),

    # Worker wallet top-ups
    path("wallet/", views.wallet_view, name="wallet"),
    path("wallet/topup/<str:method>/", views.initiate_topup_view, name="initiate_topup"),
    path("wallet/topup/esewa/callback/", views.esewa_callback_view, name="esewa_callback"),
    path("wallet/topup/esewa/failure/", views.esewa_failure_view, name="esewa_failure"),
    path("wallet/topup/khalti/callback/", views.khalti_callback_view, name="khalti_callback"),
    path("wallet/topup/<int:pk>/bank/", views.bank_topup_view, name="bank_topup"),

    path("<int:pk>/", views.payment_detail_view, name="payment_detail"),
]
