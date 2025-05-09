import logging
from datetime import timedelta

from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from accounts.models import Team, TeamScoreHistory

logger = logging.getLogger(__name__)


@require_GET
def team_score_history(request):
    """API endpoint to get team score history for chart visualization"""
    try:
        page = request.GET.get('page', '1')
        page_size = request.GET.get('page_size', '50')

        try:
            page = int(page)
            page_size = min(int(page_size), 500)
        except ValueError:
            page = 1
            page_size = 50

        days_param = request.GET.get('days', '7')

        teams_query = Team.objects.filter(is_in_game=True)

        team_uuid = request.GET.get('team_uuid', None)
        if team_uuid:
            teams_query = teams_query.filter(uuid=team_uuid)

        history_queryset = TeamScoreHistory.objects.order_by('timestamp')

        if days_param != 'all':
            try:
                days = int(days_param)
                since_date = timezone.now() - timedelta(days=days)
                history_queryset = history_queryset.filter(timestamp__gte=since_date)
            except ValueError:
                since_date = timezone.now() - timedelta(days=7)
                history_queryset = history_queryset.filter(timestamp__gte=since_date)

        teams = teams_query.prefetch_related(
            Prefetch(
                'score_history',
                queryset=history_queryset,
                to_attr='filtered_history'
            )
        ).order_by('-score', 'name')

        if team_uuid is None:
            paginator = Paginator(teams, page_size)
            teams_page = paginator.get_page(page)
            teams = teams_page.object_list
            pagination_info = {
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': teams_page.has_next(),
                'has_previous': teams_page.has_previous(),
            }
        else:
            pagination_info = None

        result = {}
        for team in teams:
            history = team.filtered_history

            team_uuid_str = str(team.uuid)
            result[team_uuid_str] = {
                'name': team.name,
                'timestamps': [entry.timestamp.isoformat() for entry in history],
                'scores': [entry.score for entry in history],
                'blue_points': [entry.blue_points for entry in history],
                'red_points': [entry.red_points for entry in history],
            }

        response_data = {'teams': result}
        if pagination_info:
            response_data['pagination'] = pagination_info

        return JsonResponse(response_data)
    except Exception as e:
        logger.exception("Error generating team score history: %s", str(e))
        return JsonResponse({'error': str(e)}, status=500)
