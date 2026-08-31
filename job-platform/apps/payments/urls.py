from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("contract/<int:contract_pk>/pay/", views.initiate_payment_view, name="initiate_payment"),
    path("contract/<int:contract_pk>/process/", views.process_payment_view, name="process_payment"),
    path("success/<int:pk>/", views.payment_success_view, name="payment_success"),
    path("failed/<int:pk>/", views.payment_failed_view, name="payment_failed"),
    path("<int:pk>/", views.payment_detail_view, name="payment_detail"),
    path("history/", views.transaction_history_view, name="transaction_history"),
    path("platform-wallet/", views.platform_wallet_view, name="platform_wallet"),
]
