from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.forms.auth_forms import UserRegistrationForm, UserLoginForm, UserSettingsForm


def register_view(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = UserRegistrationForm()
    return render(request, "registration/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("home")
    else:
        form = UserLoginForm()
    return render(request, "registration/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("home")


# noinspection PyUnresolvedReferences
@login_required
def settings_view(request):
    if request.method == "POST":
        form = UserSettingsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your settings have been updated successfully.")
            return redirect("settings")
    else:
        form = UserSettingsForm(instance=request.user)

    ssh_key_locked = form.is_ssh_key_locked()

    context = {
        "form": form,
        "user_team": request.user.team,
        "can_manage_team": (
            request.user.team and request.user.team.can_manage_members(request.user)
            if request.user.team
            else False
        ),
        "ssh_key_locked": ssh_key_locked,
    }
    return render(request, "settings/main.html", context)
