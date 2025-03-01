import logging

from django.core.management.base import BaseCommand

from ctf.models import GameContainer, GameSession, Team
from ctf.models.exceptions import ContainerOperationError, DockerOperationError
from ctf.services import DockerService, ContainerService

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
        game_containers = GameContainer.objects.all()
        teams = Team.objects.all()

        if game_sessions.count() == 0 and game_containers.count() == 0:
            logger.error("No game sessions or containers found")
            return

        game_sessions.delete()

        for container in game_containers:
            self.container_service.delete_game_container(container)

        self.docker_service.prune_images()
        self.docker_service.clean_networks()

        # Delete teams
        teams.delete()
