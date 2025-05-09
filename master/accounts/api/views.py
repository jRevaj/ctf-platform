import logging

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from accounts.models import Team, TeamScoreHistory

logger = logging.getLogger(__name__)


@require_GET
def team_score_history(request):
    """API endpoint to get team score history for chart visualization"""
    try:
        teams = Team.objects.filter(is_in_game=True).order_by('-score')
        result = {}

        # Get all teams data or specific team if requested
        team_uuid = request.GET.get('team_uuid', None)
        if team_uuid:
            teams = teams.filter(uuid=team_uuid)

        # Get data for the requested time period
        for team in teams:
            history = TeamScoreHistory.objects.filter(team=team).order_by('timestamp')

            # Limit by date if specified
            days = request.GET.get('days', None)
            if days:
                from django.utils import timezone
                import datetime
                start_date = timezone.now() - datetime.timedelta(days=int(days))
                history = history.filter(timestamp__gte=start_date)

            # Convert UUID to string for JSON serialization
            team_uuid_str = str(team.uuid)
            result[team_uuid_str] = {
                'name': team.name,
                'timestamps': [entry.timestamp.isoformat() for entry in history],
                'scores': [entry.score for entry in history],
                'blue_points': [entry.blue_points for entry in history],
                'red_points': [entry.red_points for entry in history],
            }

        return JsonResponse({'teams': result})
    except Exception as e:
        logger.exception("Error generating team score history: %s", str(e))
        return JsonResponse({'error': str(e)}, status=500)
