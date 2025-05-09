import json
from datetime import timedelta

from django.db.models import Prefetch
from django.shortcuts import render
from django.utils import timezone

from accounts.models import Team, TeamScoreHistory
from challenges.utils.view_helpers import get_user_challenges


def home(request):
    context = get_user_challenges(request.user)
    return render(request, "home.html", context)


def scoreboard_view(request):
    """Display the scoreboard with teams sorted by score"""
    days_param = request.GET.get('days', '7')

    history_queryset = TeamScoreHistory.objects.order_by('timestamp')

    if days_param != 'all':
        try:
            days = int(days_param)
            since_date = timezone.now() - timedelta(days=days)
            history_queryset = history_queryset.filter(timestamp__gte=since_date)
        except ValueError:
            since_date = timezone.now() - timedelta(days=7)
            history_queryset = history_queryset.filter(timestamp__gte=since_date)

    teams = Team.objects.filter(is_in_game=True).prefetch_related(
        Prefetch(
            'score_history',
            queryset=history_queryset,
            to_attr='filtered_history'
        )
    ).order_by('-score', 'name')

    score_history = {}
    for team in teams:
        history = team.filtered_history

        if history:
            score_history[str(team.uuid)] = {
                'name': team.name,
                'timestamps': [entry.timestamp.isoformat() for entry in history],
                'scores': [entry.score for entry in history],
                'blue_points': [entry.blue_points for entry in history],
                'red_points': [entry.red_points for entry in history],
            }

    context = {
        "teams": teams,
        "score_history_json": json.dumps(score_history),
        "days": days_param,
    }
    return render(request, "scoreboard.html", context)
