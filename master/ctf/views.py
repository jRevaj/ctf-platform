import uuid

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404

from ctf.forms.auth_forms import UserRegistrationForm, UserLoginForm, UserSettingsForm
from ctf.forms.team_forms import CreateTeamForm, JoinTeamForm
from ctf.models import User


def home(request):
    return render(request, "home.html")


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

    context = {
        "form": form,
        "user_team": request.user.team,
        "can_manage_team": (
            request.user.team and request.user.team.can_manage_members(request.user)
            if request.user.team
            else False
        ),
    }
    return render(request, "settings/main.html", context)


@login_required
def create_team_view(request):
    if request.user.team:
        messages.error(request, "You are already in a team.")
        return redirect("settings")

    if request.method == "POST":
        form = CreateTeamForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                team = form.save(commit=False)
                team.created_by = request.user
                team.save()
                request.user.team = team
                request.user.save()
            messages.success(request, f"Team {team.name} created successfully!")
            return redirect("team_details")
    else:
        form = CreateTeamForm()

    return render(request, "settings/create_team.html", {"form": form})


@login_required
def join_team_view(request):
    if request.user.team:
        messages.error(request, "You are already in a team.")
        return redirect("settings")

    if request.method == "POST":
        form = JoinTeamForm(request.POST, user=request.user)
        if form.is_valid():
            team = form.cleaned_data["join_key"]
            with transaction.atomic():
                request.user.team = team
                request.user.save()
                team.clean()
                team.save()
            messages.success(request, f"Successfully joined team {team.name}!")
            return redirect("team_details")
    else:
        form = JoinTeamForm(user=request.user)

    return render(request, "settings/join_team.html", {"form": form})


# noinspection PyUnresolvedReferences
@login_required
def team_management_view(request):
    if not request.user.team:
        messages.error(request, "You are not in a team.")
        return redirect("settings")

    context = {
        "user_team": request.user.team,
        "can_manage_team": (
            request.user.team.can_manage_members(request.user)
            if request.user.team
            else False
        ),
    }
    return render(request, "settings/team_details.html", context)


# noinspection PyUnresolvedReferences
@login_required
def remove_team_member_view(request, member_id):
    if not request.user.team:
        messages.error(request, "You are not in a team.")
        return redirect("settings")

    member_to_remove = get_object_or_404(User, id=member_id)

    try:
        with transaction.atomic():
            request.user.team.remove_member(request.user, member_to_remove)
        messages.success(
            request, f"Successfully removed user {member_to_remove.username} from the team."
        )
    except (PermissionDenied, ValidationError) as e:
        messages.error(request, str(e))

    return redirect("team_details")


# noinspection PyUnresolvedReferences
@login_required
def regenerate_team_key_view(request):
    if not request.user.team or request.user.team.created_by != request.user:
        messages.error(
            request, "You do not have permission to regenerate the team key."
        )
        return redirect("team_details")

    if request.user.team.is_in_game:
        messages.error(request, "Cannot regenerate team key while in a game.")
        return redirect("team_details")

    # Generate a new UUID for the join key
    request.user.team.join_key = uuid.uuid4()
    request.user.team.save()

    messages.success(request, "Team join key has been regenerated.")
    return redirect("team_details")
