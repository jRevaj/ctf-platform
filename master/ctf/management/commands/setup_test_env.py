import os
import uuid
import logging

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from ctf.models import ContainerTemplate, GameContainer, GameSession, GameSessionStatus, Team, TeamRole, User
from ctf.models.exceptions import ContainerOperationError, DockerOperationError
from ctf.services import DockerService, ContainerService, FlagService

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
            self._validate_environment()

            run_id = uuid.uuid4()
            blue_team, red_team = self._create_teams(run_id)
            self._create_users(run_id, blue_team, red_team)

            session = self._create_session()
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
    def _get_template(template_folder: str) -> ContainerTemplate:
        if template_folder:
            try:
                return ContainerTemplate.objects.get(folder=template_folder)
            except ContainerTemplate.DoesNotExist:
                raise ValueError(f"Template {template_folder} not found")
        return ContainerTemplate.objects.get(folder="base")

    @staticmethod
    def _validate_environment() -> None:
        if not os.getenv("TEST_BLUE_SSH_PUBLIC_KEY") or not os.getenv("TEST_RED_SSH_PUBLIC_KEY"):
            raise ValueError("TEST_BLUE_SSH_PUBLIC_KEY or TEST_RED_SSH_PUBLIC_KEY environment variable is not set")

    @staticmethod
    def _create_teams(run_id: uuid.UUID) -> tuple[Team, Team]:
        blue_team = Team.objects.create(name=f"Blue Team {run_id}", role=TeamRole.BLUE)
        red_team = Team.objects.create(name=f"Red Team {run_id}", role=TeamRole.RED)
        return blue_team, red_team

    @staticmethod
    def _create_users(run_id: uuid.UUID, blue_team: Team, red_team: Team) -> None:
        User.objects.create(
            username=f"test-{run_id}",
            email=f"test-{run_id}@example.com",
            ssh_public_key=os.getenv("TEST_BLUE_SSH_PUBLIC_KEY"),
            is_active=True,
            team=blue_team,
        )
        User.objects.create(
            username=f"testing-{run_id}",
            email=f"testing-{run_id}@example.com",
            ssh_public_key=os.getenv("TEST_RED_SSH_PUBLIC_KEY"),
            is_active=True,
            team=red_team,
        )

    @staticmethod
    def _create_session() -> GameSession:
        return GameSession.objects.create(
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
            rotation_period=1,
            status=GameSessionStatus.ACTIVE,
        )

    def _create_container(self, template: ContainerTemplate, session: GameSession, blue_team: Team, red_team: Team) -> GameContainer:
        try:
            container = self.container_service.create_game_container(
                template=template,
                session=session,
                blue_team=blue_team,
                red_team=red_team,
            )

            self.flag_service.create_and_deploy_flag(container)

            return container
        except Exception as e:
            logger.error(f"Error creating container: {e}")
            raise e

    def _print_success_message(self, container: GameContainer) -> None:
        self.stdout.write(self.style.SUCCESS(f"Test environment created successfully!"))
        ssh_string = self.container_service.get_ssh_connection_string(container)
        self.stdout.write(self.style.SUCCESS(f"Game container SSH connection string: {ssh_string}"))
