from django.urls import path
from . import views

app_name = "contracts"

urlpatterns = [
    path("", views.contract_list_view, name="contract_list"),
    path("<int:pk>/", views.contract_detail_view, name="contract_detail"),
    path("<int:pk>/complete/", views.mark_job_completed_view, name="mark_completed"),
]
