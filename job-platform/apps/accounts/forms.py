from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import CustomUser, ClientProfile, WorkerProfile, WorkerAvailability


class RegisterForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[(CustomUser.Role.CLIENT, "Client - I want to post jobs"),
                 (CustomUser.Role.WORKER, "Worker - I want to find jobs")]
    )
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ["username", "email", "role", "password1", "password2"]


class ClientProfileForm(forms.ModelForm):
    class Meta:
        model = ClientProfile
        fields = ["company_name", "bio"]


class WorkerProfileForm(forms.ModelForm):
    class Meta:
        model = WorkerProfile
        fields = ["skills", "bio", "experience_years", "hourly_rate", "resume"]


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name", "email", "phone", "address", "profile_picture"]


class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = WorkerAvailability
        fields = [
            "is_available_today",
            "available_from",
            "available_to",
            "preferred_distance_km",
            "preferred_work_types",
        ]
        widgets = {
            "available_from": forms.TimeInput(attrs={"type": "time"}),
            "available_to": forms.TimeInput(attrs={"type": "time"}),
            "preferred_work_types": forms.TextInput(
                attrs={"placeholder": "e.g. Moving, Delivery, Cleaning"}
            ),
        }
