from django.urls import path
from . import views

app_name = "reviews"

urlpatterns = [
    path("contract/<int:contract_pk>/create/", views.create_review_view, name="create_review"),
    path("user/<int:user_pk>/", views.review_list_view, name="review_list"),
]
