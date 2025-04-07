from django.db.models import Count
from django.utils import timezone

from ctf.models import GameSession, TeamAssignment, Team
from ctf.models.enums import GameSessionStatus, TeamRole
from ctf.services import ContainerService


def get_user_challenges(user):
    """
    Get challenges for a user's team, showing only one entry per session
    with priority: active red > active blue > completed
    """
    active_challenges = []
    completed_challenges = []
    container_service = ContainerService()

    if user.is_authenticated and user.team:
        now = timezone.now()

        sessions = GameSession.objects.filter(
            team_assignments__team=user.team
        ).distinct()

        processed_session_ids = set()

        for session in sessions:
            if session.id in processed_session_ids:
                continue

            processed_session_ids.add(session.id)

            if session.status == GameSessionStatus.COMPLETED:
                assignment = TeamAssignment.objects.filter(
                    team=user.team,
                    session=session
                ).select_related(
                    'session',
                    'deployment',
                    'deployment__template'
                ).prefetch_related(
                    'deployment__containers'
                ).order_by('-end_date').first()

                if assignment:
                    completed_challenges.append(assignment)
                continue

            if session.status == GameSessionStatus.ACTIVE:
                red_assignment = TeamAssignment.objects.filter(
                    team=user.team,
                    session=session,
                    role=TeamRole.RED,
                    start_date__lte=now,
                    end_date__gte=now
                ).select_related(
                    'session',
                    'deployment',
                    'deployment__template'
                ).prefetch_related(
                    'deployment__containers'
                ).first()

                if red_assignment:
                    active_challenges.append(red_assignment)
                    continue

                blue_assignment = TeamAssignment.objects.filter(
                    team=user.team,
                    session=session,
                    role=TeamRole.BLUE,
                    start_date__lte=now,
                    end_date__gte=now
                ).select_related(
                    'session',
                    'deployment',
                    'deployment__template'
                ).prefetch_related(
                    'deployment__containers'
                ).first()

                if blue_assignment:
                    active_challenges.append(blue_assignment)

        active_challenges.sort(key=lambda x: x.start_date)
        for challenge_list in [active_challenges, completed_challenges]:
            for challenge in challenge_list:
                for container in challenge.deployment.containers.all():
                    if container.is_entrypoint:
                        container.connection_string = container_service.get_ssh_connection_string(container)

    return {
        "active_challenges": active_challenges,
        "completed_challenges": completed_challenges
    }


def is_first_session_for_teams(teams):
    """
    Determine if this is the first completed session for these teams.
    For simplicity, check if any team has participated in a completed session.
    """
    team_ids = [team.id for team in teams]
    completed_counts = Team.objects.filter(
        id__in=team_ids,
        assignments__session__status=GameSessionStatus.COMPLETED
    ).annotate(completed_count=Count('assignments__session', distinct=True))

    return not completed_counts.filter(completed_count__gt=0).exists()
