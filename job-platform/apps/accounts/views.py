from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib import messages
from django.shortcuts import render, redirect

from .forms import RegisterForm, UserUpdateForm, ClientProfileForm, WorkerProfileForm, AvailabilityForm


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully.")
            return redirect("core:dashboard")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("core:dashboard")
    else:
        form = AuthenticationForm()
    return render(request, "accounts/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    return redirect("core:home")


@login_required
def profile_view(request):
    return render(request, "accounts/profile.html", {"user_obj": request.user})


@login_required
def edit_profile_view(request):
    user_form = UserUpdateForm(request.POST or None, request.FILES or None, instance=request.user)
    profile_form = None

    if request.user.is_client:
        profile_form = ClientProfileForm(request.POST or None, instance=request.user.client_profile)
    elif request.user.is_worker:
        profile_form = WorkerProfileForm(
            request.POST or None, request.FILES or None, instance=request.user.worker_profile
        )

    if request.method == "POST":
        if user_form.is_valid() and (profile_form is None or profile_form.is_valid()):
            user_form.save()
            if profile_form:
                profile_form.save()
            messages.success(request, "Profile updated.")
            return redirect("accounts:profile")

    return render(
        request, "accounts/edit_profile.html", {"user_form": user_form, "profile_form": profile_form}
    )


@login_required
def change_password_view(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully.")
            return redirect("accounts:profile")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "accounts/change_password.html", {"form": form})


@login_required
def edit_availability_view(request):
    if not request.user.is_worker:
        messages.error(request, "Only workers have availability settings.")
        return redirect("core:dashboard")

    availability = request.user.availability
    form = AvailabilityForm(request.POST or None, instance=availability)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Availability updated.")
        return redirect("accounts:profile")

    return render(request, "accounts/availability.html", {"form": form})
