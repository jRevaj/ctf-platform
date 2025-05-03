import logging

from ctf.models import TeamAssignment
from ctf.models.enums import TeamRole, GamePhaseStatus
from ctf.services import ContainerService, DeploymentService

logger = logging.getLogger(__name__)


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

            blue_completed = blue_phase and blue_phase.status == GamePhaseStatus.COMPLETED
            red_completed = red_phase and red_phase.status == GamePhaseStatus.COMPLETED

            display_assignment = None

            blue_assignment = None
            red_assignment = None
            for challenge in session_challenges:
                if challenge.role == TeamRole.BLUE:
                    blue_assignment = challenge
                elif challenge.role == TeamRole.RED:
                    red_assignment = challenge

            if blue_phase and blue_phase.status == GamePhaseStatus.ACTIVE and blue_assignment:
                display_assignment = blue_assignment
            elif blue_completed and red_phase and red_phase.status == GamePhaseStatus.ACTIVE and red_assignment:
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


def get_session_time_restrictions(challenge, team) -> tuple[bool, int, float, float, bool]:
    """
    Get time restriction information for a challenge.
    
    Returns:
        tuple: (has_time_restriction, max_time, time_spent, remaining_time, time_exceeded)
            - has_time_restriction: Whether time restrictions are enabled
            - max_time: Maximum time allowed in minutes
            - time_spent: Time spent by the team in minutes
            - remaining_time: Time remaining in minutes
            - time_exceeded: Whether the time limit has been exceeded
    """
    deployment_service = DeploymentService()
    session = challenge.session
    has_time_restriction = session.enable_time_restrictions
    max_time = session.get_max_time_for_role(challenge.role)
    time_spent = deployment_service.get_team_total_access_time_for_deployment(team, challenge.deployment)
    remaining_time = max_time - time_spent if max_time > 0 else 0
    time_exceeded = time_spent >= max_time if max_time > 0 else False

    logger.info(f"Time restrictions for challenge {challenge.uuid}: "
                f"max_time={max_time}, time_spent={time_spent}, "
                f"remaining_time={remaining_time}, time_exceeded={time_exceeded}")

    return has_time_restriction, max_time, time_spent, remaining_time, time_exceeded


def can_perform_time_restricted_action(challenge, team) -> bool:
    """
    Check if a team has exceeded their time limit for a challenge.
    
    Args:
        challenge: The TeamAssignment object
        team: The Team object
    
    Returns:
        bool: True if time limit is exceeded (user CANNOT perform actions), 
              False if within time limit or no restrictions apply
    """
    deployment_service = DeploymentService()
    session = challenge.session
    if session.enable_time_restrictions:
        max_time = session.get_max_time_for_role(challenge.role)
        if max_time <= 0:
            return False

        time_spent = deployment_service.get_team_total_access_time_for_deployment(team, challenge.deployment)
        return time_spent >= max_time
    else:
        return False
