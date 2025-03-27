import logging

from django.utils import timezone

from ctf.models import Flag, Team
from ctf.services.docker_service import DockerService

logger = logging.getLogger(__name__)


# TODO: rewrite based on new points logic (blue and red points with score calculated)
class FlagService:
    def __init__(self, docker_service=None):
        self.docker_service = docker_service or DockerService()
    
    def distribute_points(self, flag: Flag, team: Team, points: int) -> None:
        """Handle points distribution between teams"""
        # TODO: Add points distribution logic
        team.update_score(points)

        if flag.owner:
            flag.owner.update_score(-points)

    def calculate_points(self, flag: Flag) -> int:
        """Calculate points based on time since flag creation"""
        base_points = flag.points
        time_factor = 1.0

        hours_since_creation = (timezone.now() - flag.created_at).total_seconds() / 3600
        if hours_since_creation > 24:
            time_factor = max(0.5, 1 - (hours_since_creation - 24) / 48)

        return int(base_points * time_factor)

    def verify_and_capture_flag(self, team: Team, submitted_flag: str) -> tuple[bool, str]:
        """Verify and capture a flag with points calculation"""
        try:
            flag = Flag.objects.verify_flag(team, submitted_flag)
            if not flag:
                return False, "Invalid flag"

            # Calculate points based on time taken
            # points = self._calculate_points(flag)

            # Update scores
            self.distribute_points(flag, team, flag.points)

            # Mark flag as captured
            flag.capture(team)

            return True, f"Flag captured! Points awarded: {flag.points}"

        except Exception as e:
            logger.error(f"Error processing flag submission: {e}")
            return False, str(e)

    def assign_flag_owner(self, flag, team):
        """Assign ownership of a flag to a team"""
        try:
            flag.assign_owner(team)
            logger.info(f"Successfully assigned flag {flag.value} to team {team.name}")
            return True
        except Exception as e:
            logger.error(f"Error assigning flag ownership: {e}")
            return False

    # def create_and_deploy_flag(self, container: GameContainer, points=100):
    #     """Deploy a single flag to a container"""
    #     try:
    #         flag = Flag.objects.create_flag(container=container, points=points)

    #         if not flag:
    #             raise Exception("Failed to create flag")

    #         logger.info(f"Successfully created flag {flag.value}")
    #         self.docker_service.deploy_flag(container, flag)

    #         logger.info(f"Successfully deployed flag {flag.value} to container {container.name}")
    #         return flag
    #     except Exception as e:
    #         logger.error(f"Error deploying flag: {e}")
    #         return None

# Legacy function wrappers for backwards compatibility
def distribute_points(flag: Flag, team: Team, points: int) -> None:
    """Legacy wrapper for backwards compatibility"""
    FlagService().distribute_points(flag, team, points)

def calculate_points(flag: Flag) -> int:
    """Legacy wrapper for backwards compatibility"""
    return FlagService().calculate_points(flag)

def verify_and_capture_flag(team: Team, submitted_flag: str) -> tuple[bool, str]:
    """Legacy wrapper for backwards compatibility"""
    return FlagService().verify_and_capture_flag(team, submitted_flag)

def assign_flag_owner(flag, team):
    """Legacy wrapper for backwards compatibility"""
    return FlagService().assign_flag_owner(flag, team)
