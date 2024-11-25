import logging
from ctf.managers.flag_manager import FlagManager
from django.utils import timezone

from ctf.models import Flag, Team
from ctf.services import DockerService

logger = logging.getLogger(__name__)

class FlagService:
    def __init__(self):
        self.flag_manager = Flag.objects
        self.docker_service = DockerService()

    def deploy_flag(self, container, points=100):
        """Deploy a single flag to a container"""
        try:
            flag = self.flag_manager.create_flag(
                container=container,
                points=points,
                docker_service=self.docker_service
            )
            if flag:
                logger.info(f"Successfully deployed flag to container {container.name}")
                return flag
            else:
                logger.error(f"Failed to deploy flag to container {container.name}")
                return None
        except Exception as e:
            logger.error(f"Error deploying flag: {e}")
            return None

    def verify_and_capture_flag(self, team: Team, submitted_flag: str) -> tuple[bool, str]:
        """Verify and capture a flag with points calculation"""
        try:
            flag = self.flag_manager.verify_flag(team, submitted_flag)
            if not flag:
                return False, "Invalid flag"

            # Calculate points based on time taken
            # points = self._calculate_points(flag)
            
            # Update scores
            self._distribute_points(flag, team, flag.points)
            
            # Mark flag as captured
            flag.capture(team)
            
            return True, f"Flag captured! Points awarded: {flag.points}"

        except Exception as e:
            logger.error(f"Error processing flag submission: {e}")
            return False, str(e)

    def _calculate_points(self, flag: Flag) -> int:
        """Calculate points based on time since flag creation"""
        base_points = flag.points
        time_factor = 1.0
        
        hours_since_creation = (timezone.now() - flag.created_at).total_seconds() / 3600
        if hours_since_creation > 24:
            time_factor = max(0.5, 1 - (hours_since_creation - 24) / 48)
            
        return int(base_points * time_factor)

    def _distribute_points(self, flag: Flag, team: Team, points: int) -> None:
        """Handle points distribution between teams"""
        # TODO: Add points distribution logic
        team.update_score(points)
        
        if flag.owner:
            flag.owner.update_score(-points)
