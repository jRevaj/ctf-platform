from django.shortcuts import render

from accounts.models import Team
from ctf.utils.view_helpers import get_user_challenges


def home(request):
    context = get_user_challenges(request.user)
    return render(request, "home.html", context)


def scoreboard_view(request):
    """Display the scoreboard with teams sorted by score"""
    teams = Team.objects.filter(is_in_game=True).order_by('-score', 'name')
    return render(request, "scoreboard.html", {"teams": teams})
