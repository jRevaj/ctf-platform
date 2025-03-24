import logging
import uuid
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from ctf.management.commands.utils import create_teams
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
            "--session",
            type=str,
            help="Game session name",
            required=True
        )
        parser.add_argument(
            "--template",
            type=str,
            help=Challenge template name",
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
            session_name = options["session"]
            template_name = options["template"]
            number_of_teams = options["teams"]

            # Prepare necessary db objects
            try:
                template = ChallengeTemplate.objects.get(name=template_name)
                session = GameSession.objects.create(
                    name=f"{session_name} {run_id}",
                    template=template,
                    end_date=timezone.now(),
                    rotation_period=1,
                    status=GameSessionStatus.PLANNED
                )
                phase = GamePhase.objects.create(
                    session=session,
                    template=template,
                    start_date=timezone.now() - timedelta(days=session.rotation_period),
                    status='active'
                )
                teams = create_teams(run_id, number_of_teams)
            except ChallengeTemplate.DoesNotExist as e:
                logger.error(f"Error getting session or template: {e}")
                return

            logger.info(f"Testing matchmaking for session: {session.name}")
            logger.info(f"Number of teams: {len(teams)}")

            # 1. Test initial round assignments (Week 1 - Blue phase)
            logger.info("\n=== Testing Week 1 (Blue Phase) ===")
            success = self.matchmaking_service.create_round_assignments(session, teams)
            if not success:
                logger.error("Failed to create initial assignments")
                return

            # Verify blue assignments
            blue_assignments = TeamAssignment.objects.filter(
                session=session,
                role=TeamRole.BLUE,
                start_date__gte=timezone.now() - timedelta(days=1)
            ).select_related('team', 'container')

            logger.info("\nBlue Team Assignments:")
            for assignment in blue_assignments:
                logger.info(f"Team: {assignment.team.name} -> Container: {assignment.container.name}")

            # 2. Test red phase assignments (Week 2)
            logger.info("\n=== Testing Week 2 (Red Phase) ===")
            # Test random red assignments (first round)
            logger.info("\nTesting Random Red Assignments (First Round):")
            success = self.matchmaking_service.create_random_red_assignments(session, teams, phase)
            if not success:
                logger.error("Failed to create random red assignments")
                return

            # Verify red assignments
            red_assignments = TeamAssignment.objects.filter(
                session=session,
                role=TeamRole.RED,
                start_date__gte=timezone.now() - timedelta(days=1)
            ).select_related('team', 'container')

            logger.info("\nRed Team Assignments (Random):")
            for assignment in red_assignments:
                logger.info(f"Team: {assignment.team.name} -> Container: {assignment.container.name}")

            # 3. Test Swiss system assignments (Round 2+)
            logger.info("\n=== Testing Swiss System Assignments (Round 2+) ===")

            # Create a test round 2
            phase2 = GamePhase.objects.create(
                session=session,
                template=template,
                round_number=2,
                start_date=timezone.now() - timedelta(days=session.rotation_period),
                status='active'
            )

            # Test Swiss assignments
            success = self.matchmaking_service.create_swiss_assignments(session, teams)
            if not success:
                logger.error("Failed to create Swiss assignments")
                return

            # Verify Swiss assignments
            swiss_red_assignments = TeamAssignment.objects.filter(
                session=session,
                role=TeamRole.RED,
                start_date__gte=timezone.now() - timedelta(days=1)
            ).exclude(
                id__in=red_assignments.values_list('id', flat=True)
            ).select_related('team', 'container')

            logger.info("\nRed Team Assignments (Swiss System):")
            for assignment in swiss_red_assignments:
                logger.info(f"Team: {assignment.team.name} -> Container: {assignment.container.name}")

            # Cleanup test data
            phase.delete()
            phase2.delete()
            TeamAssignment.objects.filter(
                session=session,
                start_date__gte=timezone.now() - timedelta(days=1)
            ).delete()

            logger.info("\nTest completed successfully!")
        except Exception as e:
            logger.error(f"Error during testing: {e}")
