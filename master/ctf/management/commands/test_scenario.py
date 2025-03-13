import logging
import uuid

from django.core.management.base import BaseCommand

from ctf.management.commands.utils import create_teams, create_users, validate_environment
from ctf.models import ScenarioArchitecture, ScenarioTemplate
from ctf.services import DockerService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Test run a scenario"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docker_service = DockerService()

    def add_arguments(self, parser):
        parser.add_argument("scenario", nargs=1, type=str)

    def handle(self, *args, **options):
        scenario = options["scenario"][0]
        logger.info("Verifying environment and retrieving template")
        validate_environment()
        template = ScenarioTemplate.objects.get(name=scenario)

        logger.info("Generating unique run ID")
        run_id = uuid.uuid4()

        logger.info("Creating test teams")
        blue_team, red_team = create_teams(run_id)

        logger.info("Creating test users with SSH keys")
        create_users(run_id, blue_team, red_team)

        logger.info("Preparing scenario")
        containers = ScenarioArchitecture.objects.prepare_scenario(template, blue_team)

        for container in containers:
            # TODO: save connection strings to db
            logger.info(f"Connection Information for {container.name}:")
            docker_container = self.docker_service.get_container(container_id=container.docker_id)
            port = docker_container.attrs["NetworkSettings"]["Ports"]["22/tcp"][0]["HostPort"]
            logger.info(f"SSH access: ssh -p {port} ctf-user@localhost")

        logger.info(f"Scenario {run_id} deployed successfully!")
