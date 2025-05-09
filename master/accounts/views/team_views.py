import json
import uuid
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

from accounts.forms.team_forms import JoinTeamForm, CreateTeamForm
from accounts.models import Team, TeamScoreHistory, User


def teams_view(request):
    """Display all teams"""
    teams = Team.objects.all().order_by('name')
    return render(request, "teams.html", {"teams": teams})


def team_detail_view(request, team_uuid):
    """Display detailed information about a specific team"""
    days_param = request.GET.get('days', '7')

    team_query = Team.objects

    history_queryset = TeamScoreHistory.objects.order_by('timestamp')

    if days_param != 'all':
        try:
            days = int(days_param)
            since_date = timezone.now() - timedelta(days=days)
            history_queryset = history_queryset.filter(timestamp__gte=since_date)
        except ValueError:
            since_date = timezone.now() - timedelta(days=7)
            history_queryset = history_queryset.filter(timestamp__gte=since_date)

    team = get_object_or_404(
        team_query.prefetch_related(
            Prefetch(
                'score_history',
                queryset=history_queryset,
                to_attr='filtered_history'
            )
        ),
        uuid=team_uuid
    )

    score_history = {}
    if team.filtered_history:
        score_history[str(team.uuid)] = {
            'name': team.name,
            'timestamps': [entry.timestamp.isoformat() for entry in team.filtered_history],
            'scores': [entry.score for entry in team.filtered_history],
            'blue_points': [entry.blue_points for entry in team.filtered_history],
            'red_points': [entry.red_points for entry in team.filtered_history],
        }

    context = {
        "team": team,
        "score_history_json": json.dumps(score_history),
        "days": days_param
    }
    return render(request, "team_detail.html", context)


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

    request.user.team.join_key = uuid.uuid4()
    request.user.team.save()

    messages.success(request, "Team join key has been regenerated.")
    return redirect("team_details")
