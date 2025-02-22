import logging
import uuid

from django.core.management.base import BaseCommand

from ctf.models import GameContainer, GameSession, Team, ScenarioTemplate
from ctf.models.exceptions import ContainerOperationError, DockerOperationError
from .utils import validate_environment, create_teams, create_users, create_session
from ...services import DockerService, ContainerService, FlagService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Setup test environment"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docker_service = DockerService()
        self.container_service = ContainerService(self.docker_service)
        self.flag_service = FlagService()

    def add_arguments(self, parser):
        parser.add_argument("-t", "--template", dest="template", default="base", type=str, help="Template folder name")

    def handle(self, *args, **kwargs):
        self.stdout.write("Setting up test environment...")
        try:
            template = self._get_template(kwargs.get("template"))
            validate_environment()

            run_id = uuid.uuid4()
            blue_team, red_team = create_teams(run_id)
            create_users(run_id, blue_team, red_team)

            session = create_session()
            container = self._create_container(template, session, blue_team, red_team)

            if not self.container_service.configure_ssh_access(container, blue_team):
                raise ContainerOperationError("Failed to configure SSH access")

            self._print_success_message(container)

        except (ContainerOperationError, DockerOperationError) as e:
            self.stderr.write(self.style.ERROR(f"Container operation failed: {e}"))
        except ValueError as e:
            self.stderr.write(self.style.ERROR(f"Validation error: {e}"))
        except Exception as e:
            logger.exception("Unexpected error in setup_test_env")
            self.stderr.write(self.style.ERROR(f"Unexpected error: {str(e)}"))

    @staticmethod
    def _get_template(template_folder: str) -> ScenarioTemplate:
        if template_folder:
            try:
                return ScenarioTemplate.objects.get(folder=template_folder)
            except ScenarioTemplate.DoesNotExist:
                raise ValueError(f"Template {template_folder} not found")
        return ScenarioTemplate.objects.get(folder="base")

    def _create_container(self, template: ScenarioTemplate, session: GameSession, blue_team: Team,
                          red_team: Team) -> GameContainer:
        try:
            container: GameContainer = self.container_service.create_game_container(
                template=template,
                session=session,
                blue_team=blue_team,
                red_team=red_team,
            )

            # flag = self.flag_service.create_and_deploy_flag(container)
            # self.flag_service.assign_flag_owner(flag, blue_team)

            return container
        except Exception as e:
            logger.error(f"Error creating container: {e}")
            raise e

    def _print_success_message(self, container: GameContainer) -> None:
        self.stdout.write(self.style.SUCCESS(f"Test environment created successfully!"))
        ssh_string = self.container_service.get_ssh_connection_string(container)
        self.stdout.write(self.style.SUCCESS(f"Game container SSH connection string: {ssh_string}"))
