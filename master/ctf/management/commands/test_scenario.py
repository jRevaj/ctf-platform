import uuid

from django.core.management.base import BaseCommand

from ctf.management.commands.utils import create_teams, create_users, validate_environment
from ctf.models import ScenarioArchitecture, ScenarioTemplate


class Command(BaseCommand):
    help = "Test run a scenario"

    def add_arguments(self, parser):
        parser.add_argument("scenario", nargs=1, type=str)

    def handle(self, *args, **options):
        # Verify environment and scenario template exist
        scenario = options["scenario"][0]
        self.stdout.write("Verifying environment and retrieving template")
        validate_environment()
        template = ScenarioTemplate.objects.get(name=scenario)

        # Generate unique run ID
        self.stdout.write("Generating unique run ID")
        run_id = uuid.uuid4()

        # Create test teams
        self.stdout.write("Creating test teams")
        blue_team, red_team = create_teams(run_id)

        # Create test users with SSH keys
        self.stdout.write("Creating test users with SSH keys")
        create_users(run_id, blue_team, red_team)

        # Prepare scenario
        self.stdout.write("Preparing scenario")
        container = ScenarioArchitecture.objects.prepare_scenario(blue_team, red_team, template)

        # Print connection information
        self.stdout.write(self.style.SUCCESS(f"\nScenario {run_id} deployed successfully!"))
        self.stdout.write("\nConnection Information:")
        port = container.attrs["NetworkSettings"]["Ports"]["22/tcp"][0]["HostPort"]
        self.stdout.write(
            self.style.SUCCESS(f"Container {container.name} SSH access: ssh -p {port} ctf-user@localhost"))
