import logging

from django.core.management.base import BaseCommand

from ctf.models import GameSession
from ctf.services import DockerService, ContainerService
from ctf.services.matchmaking_service import MatchmakingService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Create matchmaking assignments for teams"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docker_service = DockerService()
        self.container_service = ContainerService(self.docker_service)
        self.matchmaking_service = MatchmakingService(self.container_service)

    def add_arguments(self, parser):
        parser.add_argument(
            "--session",
            type=str,
            help="Game session name",
            required=True
        )
        parser.add_argument(
            "--round-type",
            type=str,
            choices=["initial", "random", "swiss"],
            help="Type of round to create",
            required=True
        )

    def handle(self, *args, **options):
        try:
            session_name = options["session"]
            round_type = options["round_type"]

            try:
                session = GameSession.objects.get(name=session_name)
            except GameSession.DoesNotExist:
                logger.error(f"Game session {session_name} does not exist")
                return

            teams = session.get_teams()
            if not teams:
                logger.error("No teams found in the session")
                return

            success = False
            if round_type == "initial":
                success = self.matchmaking_service.create_initial_assignments(session, teams)
            elif round_type == "random":
                success = self.matchmaking_service.create_random_red_assignments(session, teams)
            elif round_type == "swiss":
                success = self.matchmaking_service.create_swiss_assignments(session, teams)

            if success:
                logger.info(f"Successfully created {round_type} assignments")
            else:
                logger.error(f"Failed to create {round_type} assignments")

        except Exception as e:
            logger.error(f"Error creating assignments: {e}")
