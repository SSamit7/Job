from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list_view, name="list"),
    path("<int:pk>/open/", views.open_notification_view, name="open"),
    path("mark-all-read/", views.mark_all_read_view, name="mark_all_read"),
]
