from django.urls import path
from . import views

app_name = "messaging"

urlpatterns = [
    path("", views.conversation_list_view, name="conversation_list"),
    path("<int:contract_pk>/", views.conversation_detail_view, name="conversation_detail"),
]
