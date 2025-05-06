import logging

from challenges.services import DeploymentService

logger = logging.getLogger(__name__)


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
