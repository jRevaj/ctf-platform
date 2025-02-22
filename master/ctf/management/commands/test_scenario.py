import logging
import uuid

from django.core.management.base import BaseCommand

from ctf.management.commands.utils import create_teams, create_users, validate_environment, verify_scenario_template
from ctf.models import ScenarioArchitecture

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Test run a scenario"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scenario_template_folder = args[0]

    def handle(self, *args, **options):
        # Verify environment and scenario template exist
        logger.info("Verifying environment and scenario template")
        validate_environment()
        verify_scenario_template(self.scenario_template_folder)

        # Generate unique run ID
        logger.info("Generating unique run ID")
        run_id = uuid.uuid4()

        # Create test teams
        logger.info("Creating test teams")
        blue_team, red_team = create_teams(run_id)

        # Create test users with SSH keys
        logger.info("Creating test users with SSH keys")
        create_users(run_id, blue_team, red_team)

        # Prepare scenario
        logger.info("Preparing scenario")
        container = ScenarioArchitecture.objects.prepare_scenario(blue_team, red_team, self.scenario_template_folder)

        # Print connection information
        logger.info("Printing connection information")
        self.stdout.write(self.style.SUCCESS(f"\nScenario {run_id} deployed successfully!"))
        self.stdout.write("\nConnection Information:")
        port = container.attrs["NetworkSettings"]["Ports"]["22/tcp"][0]["HostPort"]
        self.stdout.write(
            self.style.SUCCESS(f"Container {container.name} SSH access: ssh -p {port} ctf-user@localhost"))
