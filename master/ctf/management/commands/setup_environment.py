import logging
import uuid

from django.core.management.base import BaseCommand

from ctf.management.commands.utils import validate_environment, create_teams, create_users_with_key, create_session
from ctf.models import GameContainer, GameSession, Team, ChallengeTemplate
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

            if bool(template.containers_config) and len(dict(template.containers_config)) == 1:
                logger.info("Setting up single container challenge")
                self.setup_single_container(run_id, template)
            else:
                logger.info("Setting up multi container challenge")
                self.setup_multi_container(run_id, template)

        except (ContainerOperationError, DockerOperationError) as e:
            logger.error(f"Container operation failed: {e}")
        except ValueError as e:
            logger.error(f"Validation error: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error: {str(e)}")

    def setup_multi_container(self, run_id: uuid.UUID, template: ChallengeTemplate):
        """Setup a multi-container challenge"""
        logger.info("Creating test teams")
        teams = create_teams(run_id, 2)
        blue_team, red_team = teams[0], teams[1]
        red_team.rotate_role()

        logger.info("Creating test users with SSH keys")
        create_users_with_key(run_id, blue_team, red_team)

        logger.info("Preparing challenge")
        containers = self.challenge_service.prepare_challenge(template, blue_team)

        for container in containers:
            logger.info(f"SSH access for {container.name}: {container.get_connection_string()}")

        logger.info(f"Challenge {run_id} deployed successfully!")

    def setup_single_container(self, run_id: uuid.UUID, template: ChallengeTemplate):
        """Set up a single container environment"""
        logger.info("Creating test teams")
        teams = create_teams(run_id, 2)
        blue_team, red_team = teams[0], teams[1]
        red_team.rotate_role()

        logger.info("Creating test users with SSH keys")
        create_users_with_key(run_id, blue_team, red_team)

        session = create_session()
        container = self._create_container(template, session, blue_team)

        if not self.container_service.configure_ssh_access(container, blue_team):
            raise ContainerOperationError("Failed to configure SSH access")

        # flag = self.flag_service.create_and_deploy_flag(container)
        # self.flag_service.assign_flag_owner(flag, blue_team)

        logger.info(f"Test environment created successfully!")
        ssh_string = self.container_service.get_ssh_connection_string(container)
        logger.info(f"Game container SSH connection string: {ssh_string}")

    @staticmethod
    def _get_template(template_name: str) -> ChallengeTemplate:
        try:
            return ChallengeTemplate.objects.get(name=template_name)
        except ChallengeTemplate.DoesNotExist:
            raise ValueError(f"Template {template_name} not found")

    def _create_container(self, template: ChallengeTemplate, session: GameSession, blue_team: Team) -> GameContainer:
        try:
            container: GameContainer = self.container_service.create_game_container(
                template=template,
                temp_dir=template.folder,
                session=session,
                blue_team=blue_team,
            )
            return container
        except Exception as e:
            logger.error(f"Error creating container: {e}")
            raise e
