import logging
import uuid
from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from ctf.management.commands.utils import create_teams, create_users
from ctf.models import GameSession, GamePhase, TeamAssignment, ChallengeTemplate
from ctf.models.enums import TeamRole, GameSessionStatus
from ctf.services import DockerService, ContainerService
from ctf.services.matchmaking_service import MatchmakingService
from ctf.services.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Test the matchmaking system by simulating a round"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docker_service = DockerService()
        self.container_service = ContainerService(self.docker_service)
        self.matchmaking_service = MatchmakingService(self.container_service)
        self.scheduler_service = SchedulerService(self.matchmaking_service)

    def add_arguments(self, parser):
        parser.add_argument(
            "--round",
            type=int,
            choices=[1, 2],
            help="The round number (1 for random assignment, 2 for swiss assignment)",
            default=1,
        )
        parser.add_argument(
            "--session",
            type=str,
            help="Game session name",
            required=True
        )
        parser.add_argument(
            "--template",
            type=str,
            help="Challenge template name",
            required=True
        )
        parser.add_argument(
            "--teams",
            type=int,
            help="Number of teams to create",
            required=True
        )

    def handle(self, *args, **options):
        try:
            run_id = uuid.uuid4()
            test_round = options["round"]
            session_name = options["session"]
            template_name = options["template"]
            number_of_teams = options["teams"]

            logger.info(f"Testing matchmaking for session: {session_name}")
            logger.info(f"Number of teams: {number_of_teams}")

            template, session, phase, teams = self._prepare_objects(run_id, session_name, template_name,
                                                                    number_of_teams)

            self._simulate_first_round(session, teams)

            if test_round == 1:
                self._test_random_assignment(session, phase, teams)
            else:
                self._test_swiss_assignment(session, teams)

            logger.info("\nTest completed successfully!")
        except Exception as e:
            logger.error(f"Error during testing: {e}")
            call_command("clean_test_env")

    @staticmethod
    def _prepare_objects(run_id, session_name, template_name, number_of_teams):
        try:
            logger.info("Preparing necessary objects")
            template = ChallengeTemplate.objects.get(name=template_name)
            session = GameSession.objects.create(
                name=f"{session_name} {run_id}",
                template=template,
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=1),
                rotation_period=1,
                status=GameSessionStatus.PLANNED
            )
            phase = GamePhase.objects.create(
                session=session,
                template=template,
                start_date=timezone.now(),
                status='active'
            )
            users = create_users(run_id, number_of_teams * 2, True)
            teams = create_teams(run_id, number_of_teams)
            for i, user in enumerate(users):
                user.team = teams[i % number_of_teams]
                user.save()

            return template, session, phase, teams
        except ChallengeTemplate.DoesNotExist as e:
            logger.error(f"Error getting session or template: {e}")
            return

    def _simulate_first_round(self, session, teams):
        logger.info("=== Simulating Week 1 (Blue Phase) ===")
        success = self.matchmaking_service.create_round_assignments(session, teams)
        if not success:
            logger.error("Failed to create initial assignments")
            raise Exception("Failed to create initial assignments")

        logger.info("Blue Team Assignments:")
        blue_assignments = TeamAssignment.objects.filter(
            session=session,
            role=TeamRole.BLUE,
            start_date__gte=timezone.now() - timedelta(days=1)
        ).select_related('team', 'deployment')
        for assignment in blue_assignments:
            logger.info(f"Team: {assignment.team.name} -> Deployment: {assignment.deployment.pk}")

    def _test_random_assignment(self, session, phase, teams):
        logger.info("=== Testing Week 2 (Red Phase) ===")
        logger.info("Testing Random Red Assignments (First Round):")
        success = self.matchmaking_service.create_random_red_assignments(session, phase, teams)
        if not success:
            logger.error("Failed to create random red assignments")
            raise Exception("Failed to create random red assignments")

        red_assignments = TeamAssignment.objects.filter(
            session=session,
            role=TeamRole.RED,
            start_date__gte=timezone.now() - timedelta(days=1)
        ).select_related('team', 'deployment')

        logger.info("Red Team Assignments (Random):")
        for assignment in red_assignments:
            logger.info(f"Team: {assignment.team.name} -> Deployment: {assignment.deployment.pk}")

        logger.info("First round assignment tested successfully!")

    def _test_swiss_assignment(self, session, teams):
        logger.info("=== Testing Week 2 (Red Phase) ===")
        logger.info("Testing Swiss Red Assignments (2+ Round):")
        success = self.matchmaking_service.create_swiss_assignments(session, teams)
        if not success:
            logger.error("Failed to create Swiss assignments")
            return

        red_assignments = TeamAssignment.objects.filter(
            session=session,
            role=TeamRole.RED,
            start_date__gte=timezone.now() - timedelta(days=1)
        ).select_related('team', 'deployment')

        logger.info("\nRed Team Assignments (Swiss System):")
        for assignment in red_assignments:
            logger.info(f"Team: {assignment.team.name} -> Deployment: {assignment.deployment.pk}")
