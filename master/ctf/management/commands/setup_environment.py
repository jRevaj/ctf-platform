import logging
import uuid

from django.core.management.base import BaseCommand

from ctf.management.commands.utils import validate_environment, create_teams, create_users_with_key, create_session
from ctf.models import ChallengeTemplate
from ctf.models.exceptions import ContainerOperationError, DockerOperationError
from ctf.services import DockerService, ContainerService, FlagService, ChallengeService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Setup environment for testing (single container or multi-container challenge)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docker_service = DockerService()
        self.container_service = ContainerService(self.docker_service)
        self.challenge_service = ChallengeService(self.docker_service, self.container_service)
        self.flag_service = FlagService()

    def add_arguments(self, parser):
        parser.add_argument("template", type=str, help="Template name to set up")

    def handle(self, *args, **options):
        logger.info("Setting up environment...")
        try:
            run_id = uuid.uuid4()
            logger.info(f"Generated unique run ID: {run_id}")
            template_name = options.get("template")

            logger.info("Verifying environment")
            validate_environment()
            template = self._get_template(template_name)
            session = create_session(template, run_id)

            logger.info("Creating test teams")
            teams = create_teams(run_id, 2)
            blue_team, red_team = teams[0], teams[1]

            logger.info("Creating test users with SSH keys")
            create_users_with_key(run_id, blue_team, red_team)

            logger.info("Preparing challenge")
            deployment = self.challenge_service.prepare_challenge(session, blue_team)
            containers = deployment.containers.all()

            is_single_container = containers.count() == 1
            if is_single_container:
                container = containers[0]
                logger.info(f"SSH connection string: {container.get_connection_string()}")
            else:
                for container in containers:
                    logger.info(f"SSH connection string for {container.name}: {container.get_connection_string()}")

            logger.info(f"Challenge {run_id} deployed successfully!")

        except (ContainerOperationError, DockerOperationError) as e:
            logger.error(f"Container operation failed: {e}")
        except ValueError as e:
            logger.error(f"Validation error: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error: {str(e)}")

    @staticmethod
    def _get_template(template_name: str) -> ChallengeTemplate:
        try:
            return ChallengeTemplate.objects.get(name=template_name)
        except ChallengeTemplate.DoesNotExist:
            raise ValueError(f"Template {template_name} not found")
