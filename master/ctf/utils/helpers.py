from celery.schedules import crontab
from django.core.exceptions import ValidationError
from django.db.models import Count

from ctf.models.enums import GameSessionStatus


def is_first_session_for_teams(teams):
    """
    Determine if this is the first completed session for these teams.
    For simplicity, check if any team has participated in a completed session.
    """
    from ctf.models import Team
    team_ids = [team.id for team in teams]
    completed_counts = Team.objects.filter(
        id__in=team_ids,
        assignments__session__status=GameSessionStatus.COMPLETED
    ).annotate(completed_count=Count('assignments__session', distinct=True))

    return not completed_counts.filter(completed_count__gt=0).exists()


def validate_cron_expression(cron_expr, field_name):
    """Validate a cron expression format"""
    try:
        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValidationError(f"{field_name} must have 5 parts (minute hour day month weekday)")
        crontab(*parts)
    except Exception as e:
        raise ValidationError(f"{field_name} is not a valid cron expression: {e}")
