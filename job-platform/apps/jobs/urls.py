from django.urls import path
from . import views

app_name = "jobs"

urlpatterns = [
    path("", views.job_list_view, name="job_list"),
    path("create/", views.job_create_view, name="job_create"),
    path("mine/", views.my_jobs_view, name="my_jobs"),
    path("mine/<int:pk>/", views.my_job_detail_view, name="my_job_detail"),
    path("<int:pk>/", views.job_detail_view, name="job_detail"),
    path("<int:pk>/edit/", views.job_edit_view, name="job_edit"),
]
