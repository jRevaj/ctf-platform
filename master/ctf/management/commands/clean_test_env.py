import logging
import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.models import Team
from challenges.models import ChallengeContainer, ChallengeDeployment
from challenges.models.exceptions import ContainerOperationError, DockerOperationError
from challenges.services import DockerService, ContainerService
from ctf.models import GameSession, GamePhase, TeamAssignment, Flag

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Clean up test environment"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docker_service = DockerService()
        self.container_service = ContainerService(self.docker_service)

    def handle(self, *args, **kwargs):
        try:
            logger.info("Cleaning up test environment...")
            cleaned_count = self.container_service.clean_docker_containers()
            if cleaned_count:
                logger.info(f"Cleaned up {cleaned_count} orphaned containers")
            self._cleanup_game_resources()
            logger.info("Test environment cleaned up successfully!")
        except (ContainerOperationError, DockerOperationError) as e:
            logger.error(f"Container operation failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

    def _cleanup_game_resources(self):
        game_sessions = GameSession.objects.all()
        game_containers = ChallengeContainer.objects.all()

        temp_folder = os.path.join(settings.BASE_DIR, "temp")
        if os.path.exists(temp_folder):
            shutil.rmtree(temp_folder)

        if game_sessions.count() == 0 and game_containers.count() == 0:
            logger.error("No game sessions or containers found")
            return

        game_sessions.delete()

        for container in game_containers:
            container.delete()

        self.docker_service.prune_images()
        self.docker_service.prune_networks()

        GamePhase.objects.all().delete()
        ChallengeDeployment.objects.all().delete()
        TeamAssignment.objects.all().delete()
        teams = Team.objects.all()

        for team in teams:
            for user in team.users.all():
                user.delete()
            team.delete()

        Flag.objects.all().delete()
