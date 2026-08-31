from django.urls import path
from . import views

app_name = "applications"

urlpatterns = [
    path("job/<int:job_pk>/apply/", views.apply_job_view, name="apply_job"),
    path("mine/", views.my_applications_view, name="my_applications"),
    path("received/", views.received_applications_view, name="received_applications"),
    path("<int:pk>/", views.application_detail_view, name="application_detail"),
    path("<int:pk>/select/", views.select_worker_view, name="select_worker"),
]
