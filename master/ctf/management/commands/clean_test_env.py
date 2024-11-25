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
            self.stdout.write("Cleaning up test environment...")

            cleaned_count = self.container_service.clean_docker_containers()
            if cleaned_count:
                self.stdout.write(self.style.SUCCESS(f"Cleaned up {cleaned_count} orphaned containers"))

            self._cleanup_game_resources()
            self.stdout.write(self.style.SUCCESS("Test environment cleaned up successfully!"))

        except (ContainerOperationError, DockerOperationError) as e:
            self.stderr.write(self.style.ERROR(f"Container operation failed: {e}"))
        except Exception as e:
            logger.exception("Unexpected error in clean_test_env")
            self.stderr.write(self.style.ERROR(f"Unexpected error: {e}"))

    def _cleanup_game_resources(self):
        game_sessions = GameSession.objects.all()
        game_containers = GameContainer.objects.all()
        teams = Team.objects.all()

        if game_sessions.count() == 0 and game_containers.count() == 0:
            self.stdout.write(self.style.WARNING("No game sessions or containers found"))
            return

        # Delete game sessions
        game_sessions.delete()

        # Delete containers
        for container in game_containers:
            self.container_service.delete_game_container(container)

        # Delete teams
        teams.delete()
