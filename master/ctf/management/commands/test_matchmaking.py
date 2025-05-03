import logging
import random
import uuid
from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Team
from ctf.management.commands.utils import create_teams, create_users
from ctf.models import GameSession, TeamAssignment, ChallengeTemplate, GamePhase
from ctf.models.enums import TeamRole, GameSessionStatus
from ctf.models.settings import GlobalSettings
from ctf.services import DockerService, ContainerService
from ctf.services.matchmaking_service import MatchmakingService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Test the matchmaking system by simulating a round"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docker_service = DockerService()
        self.container_service = ContainerService(self.docker_service)
        self.matchmaking_service = MatchmakingService(self.container_service)

    def add_arguments(self, parser):
        parser.add_argument(
            "--system",
            type=str,
            choices=["random", "swiss"],
            help="System to use when assigning opponents",
            default="random",
        )
        parser.add_argument(
            "--rounds",
            type=int,
            help="Number of rounds to run",
            default=1
        )
        parser.add_argument(
            "--session",
            type=str,
            help="Game session name",
            default="test",
            required=True
        )
        parser.add_argument(
            "--template",
            type=str,
            help="Challenge template name",
            default="challenge1",
            required=True
        )
        parser.add_argument(
            "--teams",
            type=int,
            help="Number of teams to create",
            default=4,
            required=True
        )

    def handle(self, *args, **options):
        try:
            run_id = uuid.uuid4()
            system = options["system"]
            num_of_rounds = options["rounds"]
            session_name = options["session"]
            template_name = options["template"]
            num_of_teams = options["teams"]

            logger.info(f"Testing matchmaking for session: {session_name}")
            logger.info(f"Number of teams: {num_of_teams}")

            template, session, teams = self._prepare_objects(run_id, session_name, template_name,
                                                             num_of_teams)
            self._handle_first_round(session, teams)

            if num_of_rounds > 1:
                for i in range(num_of_rounds):
                    if i == 0:
                        new_session = session
                        self._test_random_assignment(new_session,
                                                     new_session.phases.filter(phase_name=TeamRole.RED).first(), teams)
                    else:
                        new_session = GameSession.objects.create(
                            name=f"{session_name} {run_id} {i}",
                            template=template,
                            start_date=timezone.now(),
                            rotation_period=1,
                            status=GameSessionStatus.PLANNED
                        )
                        self._handle_first_round(new_session, teams)
                        self._test_swiss_assignment(new_session, session.phases.filter(phase_name=TeamRole.RED).first(),
                                                    teams)
                    new_session.status = GameSessionStatus.COMPLETED
                    logger.info(f"Marking session {new_session.name} as completed (turning off associated containers)")
                    new_session.save(update_fields=["status"])
                    logger.info(f"Session {new_session.name} completed successfully")
            else:
                if system == "random":
                    self._test_random_assignment(session, session.phases.filter(phase_name=TeamRole.RED).first(), teams)
                elif system == "swiss":
                    self._test_swiss_assignment(session, session.phases.filter(phase_name=TeamRole.RED).first(), teams)
                else:
                    raise Exception(f"Unknown system: {system}")

            logger.info("Test completed successfully!")
        except Exception as e:
            logger.error(f"Error during testing: {e}")
            call_command("clean_test_env")

    @staticmethod
    def _prepare_objects(run_id: uuid.UUID, session_name: str, template_name: str, number_of_teams: int) -> tuple[
        ChallengeTemplate, GameSession, list[Team]]:
        try:
            logger.info("Preparing necessary objects")
            template = ChallengeTemplate.objects.get(name=template_name)
            session = GameSession.objects.create(
                name=f"{session_name} {run_id}",
                template=template,
                start_date=timezone.now(),
                rotation_period=1,
                status=GameSessionStatus.PLANNED
            )
            users = create_users(run_id, number_of_teams * 2, True)
            teams = create_teams(run_id, number_of_teams)
            for i, user in enumerate(users):
                user.team = teams[i % number_of_teams]
                user.save(update_fields=['team'])

            return template, session, teams
        except ChallengeTemplate.DoesNotExist as e:
            raise Exception(f"Error getting session or template: {e}")

    def _handle_first_round(self, session: GameSession, teams: list[Team]) -> None:
        phases = session.phases.all()
        blue_phase = phases.get(phase_name=TeamRole.BLUE)
        self._simulate_first_round(session, blue_phase, teams)
        blue_phase.status = GameSessionStatus.COMPLETED
        blue_phase.save(update_fields=["status"])

    def _simulate_first_round(self, session: GameSession, phase: GamePhase, teams: list[Team]) -> None:
        logger.info("=== Simulating Week 1 (Blue Phase) ===")
        success = self.matchmaking_service.create_round_assignments(session, teams)
        if not success:
            raise Exception("Failed to create initial assignments")

        logger.info("Blue Team Assignments:")
        blue_assignments = TeamAssignment.objects.filter(
            session=session,
            role=TeamRole.BLUE,
            start_date__gte=timezone.now() - timedelta(days=1)
        ).select_related('team', 'deployment')
        for assignment in blue_assignments:
            logger.info(f"Team: {assignment.team.name} -> Deployment: {assignment.deployment.pk}")

        phase.status = GameSessionStatus.ACTIVE
        phase.save(update_fields=['status'])
        session.status = GameSessionStatus.ACTIVE
        session.save(update_fields=['status'])

    def _test_random_assignment(self, session: GameSession, phase: GamePhase, teams: list[Team]) -> None:
        logger.info("=== Testing Week 2 (Red Phase) ===")
        logger.info("Testing Random Red Assignments (First Round):")
        success = self.matchmaking_service.create_random_red_assignments(session, phase, teams)
        if not success:
            raise Exception("Failed to create random red assignments")

        red_assignments = TeamAssignment.objects.filter(
            session=session,
            role=TeamRole.RED,
            start_date__gte=timezone.now() - timedelta(days=1)
        ).select_related('team', 'deployment')

        logger.info("Red Team Assignments (Random):")
        for assignment in red_assignments:
            logger.info(f"Team: {assignment.team.name} -> Deployment: {assignment.deployment.pk}")

        phase.status = GameSessionStatus.ACTIVE
        phase.save(update_fields=['status'])
        logger.info("First round assignment tested successfully!")

    def _test_swiss_assignment(self, session: GameSession, phase: GamePhase, teams: list[Team]) -> None:
        logger.info("=== Testing Week 2 (Red Phase) ===")
        logger.info("Testing Swiss Red Assignments (2+ Round):")
        logger.info("Setting random points to teams")
        for team in teams:
            team.score = random.randint(0, 1000)
            team.save(update_fields=['score'])

        settings = GlobalSettings.get_settings()
        success = self.matchmaking_service.create_swiss_assignments(session, phase, teams, settings.number_of_tiers)
        if not success:
            raise Exception("Failed to create Swiss assignments")

        red_assignments = TeamAssignment.objects.filter(
            session=session,
            role=TeamRole.RED,
            start_date__gte=timezone.now() - timedelta(days=1)
        ).select_related('team', 'deployment')

        logger.info("Red Team Assignments (Swiss System):")
        for assignment in red_assignments:
            logger.info(f"Team: {assignment.team.name} -> Deployment: {assignment.deployment.pk}")

        phase.status = GameSessionStatus.ACTIVE
        phase.save(update_fields=['status'])
        logger.info("Swiss round assignment tested successfully!")
