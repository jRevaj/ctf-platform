from django.db.models import Count

from ctf.models import TeamAssignment, Team
from ctf.models.enums import GameSessionStatus, TeamRole
from ctf.services import ContainerService


def get_user_challenges(user):
    """
    Get all challenges for a user's team, ordered by session start date.
    Phase logic:
    - If blue phase is active = show blue phase only
    - If blue is completed and red active = show red phase only
    - If both completed = pass the last active phase with appended is_completed = True
    """
    challenges = []
    container_service = ContainerService()

    if user.is_authenticated and user.team:
        assignments = TeamAssignment.objects.filter(
            team=user.team
        ).select_related('session', 'deployment', 'deployment__template').prefetch_related(
            'deployment__containers',
            'session__phases'
        ).order_by('session__start_date')

        session_assignments = {}
        for assignment in assignments:
            session_id = assignment.session.id
            if session_id not in session_assignments:
                session_assignments[session_id] = []
            session_assignments[session_id].append(assignment)

        for session_id, session_challenges in session_assignments.items():
            session = session_challenges[0].session
            blue_phase = session.phases.filter(phase_name=TeamRole.BLUE).first()
            red_phase = session.phases.filter(phase_name=TeamRole.RED).first()

            blue_completed = blue_phase and blue_phase.status == GameSessionStatus.COMPLETED
            red_completed = red_phase and red_phase.status == GameSessionStatus.COMPLETED

            display_assignment = None

            blue_assignment = None
            red_assignment = None
            for challenge in session_challenges:
                if challenge.role == TeamRole.BLUE:
                    blue_assignment = challenge
                elif challenge.role == TeamRole.RED:
                    red_assignment = challenge

            if blue_phase and blue_phase.status == GameSessionStatus.ACTIVE and blue_assignment:
                display_assignment = blue_assignment
            elif blue_completed and red_phase and red_phase.status == GameSessionStatus.ACTIVE and red_assignment:
                display_assignment = red_assignment
            elif blue_completed and red_completed and red_assignment:
                display_assignment = red_assignment

            if display_assignment:
                for container in display_assignment.deployment.containers.all():
                    if container.is_entrypoint:
                        container.connection_string = container_service.get_ssh_connection_string(container)

                display_assignment.is_completed = blue_completed and red_completed
                challenges.append(display_assignment)

        challenges.sort(key=lambda x: x.session.start_date)

    return {
        "challenges": challenges
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
