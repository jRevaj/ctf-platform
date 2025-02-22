import logging
from django.core.management.base import BaseCommand, CommandError
import os
import uuid

from ctf.services.docker_service import DockerService
from django.conf import settings

from ctf.management.commands.utils import create_teams, create_users, validate_environment
from ctf.managers.scenario_manager import ScenarioArchitectureManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Test run a scenario"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scenario_template_folder = args[0]
        self.docker_service = DockerService()
        self.scenario_manager = ScenarioArchitectureManager()

    def handle(self, *args, **options):
        # Verify environment and scenario template exist
        logger.info("Verifying environment and scenario template")
        validate_environment()
        self._verify_scenario_template(self.scenario_template_folder)

        # Generate unique run ID
        logger.info("Generating unique run ID")
        run_id = str(uuid.uuid4())[:8]

        # Create test teams
        logger.info("Creating test teams")
        blue_team, red_team = create_teams(run_id)

        # Create test users with SSH keys
        logger.info("Creating test users with SSH keys")
        create_users(run_id, blue_team, red_team)

        # Prepare scenario
        logger.info("Preparing scenario")
        container = self.scenario_manager.prepare_scenario(blue_team, red_team, self.scenario_template_folder)
        
        # Print connection information
        logger.info("Printing connection information")
        self.stdout.write(self.style.SUCCESS(f"\nScenario {run_id} deployed successfully!"))
        self.stdout.write("\nConnection Information:")
        port = container.attrs["NetworkSettings"]["Ports"]["22/tcp"][0]["HostPort"]
        self.stdout.write(self.style.SUCCESS(f"Container {container.name} SSH access: ssh -p {port} ctf-user@localhost"))

    def _verify_scenario_template(self, scenario_template_folder: str) -> None:
        base_path = os.path.join(settings.BASE_DIR, "game-scenarios", scenario_template_folder)
        if not os.path.exists(base_path):
            raise CommandError(f"Scenario template directory not found: {base_path}")
        
        if not os.path.exists(os.path.join(base_path, "docker-compose.yaml")):
            raise CommandError(f"docker-compose.yaml not found in {base_path}")
        
        if not os.path.exists(os.path.join(base_path, "scenario.yaml")):
            raise CommandError(f"scenario.yaml not found in {base_path}")
