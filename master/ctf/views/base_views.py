from django.shortcuts import render
import json
from django.utils import timezone
from datetime import timedelta

from accounts.models import Team, TeamScoreHistory
from challenges.utils.view_helpers import get_user_challenges


def home(request):
    context = get_user_challenges(request.user)
    return render(request, "home.html", context)


def scoreboard_view(request):
    """Display the scoreboard with teams sorted by score"""
    teams = Team.objects.filter(is_in_game=True).order_by('-score', 'name')

    score_history = {}
    for team in teams:
        history = TeamScoreHistory.objects.filter(
            team=team,
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).order_by('timestamp')
        
        if history.exists():
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
    }
    return render(request, "scoreboard.html", context)
