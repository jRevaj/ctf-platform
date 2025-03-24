import logging

from django.core.management.base import BaseCommand

# Direct imports to avoid circular dependencies
from ctf.services.docker_service import DockerService
from ctf.services.container_service import ContainerService
from ctf.services.matchmaking_service import MatchmakingService
from ctf.services.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process scheduled phases and handle automatic rotations"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docker_service = DockerService()
        self.container_service = ContainerService(self.docker_service)
        self.matchmaking_service = MatchmakingService(self.container_service)
        self.scheduler_service = SchedulerService(self.matchmaking_service)

    def handle(self, *args, **options):
        try:
            logger.info("Processing scheduled phases...")
            self.scheduler_service.process_scheduled_rounds()
            logger.info("Successfully processed scheduled phases")
        except Exception as e:
            logger.error(f"Error processing phases: {e}")
