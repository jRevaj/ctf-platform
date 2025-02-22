import logging
import os
from pathlib import Path
import shutil
from django.db import models

from ctf.management.commands.utils import create_session
from ctf.models.exceptions import ContainerOperationError, DockerOperationError
from ctf.models.flag import Flag
from ctf.services.docker_service import DockerService

# scenario.yaml
# name: scenario1
# title: Base multi-container scenario
# description: Scenario with multiple containers in one network and multiple services per container
# containers:
#   target1:
#     name: target1
#     services:
#       - name: "SSH"
#         port: 22
#       - name: "Apache"
#         port: 80
#       - name: "MySQL"
#         port: 3306
#     flags:
#       - placeholder: "FLAG_PLACEHOLDER_1"
#         points: 100
#         deployment_path: "/var/www/hidden/secret.txt"
#         hint: "Check web server configurations"
#         service: "Apache"
#       - placeholder: "FLAG_PLACEHOLDER_2"
#         points: 200
#         deployment_path: "/var/lib/mysql/flag.txt"
#         hint: "Database permissions might be loose"
#         service: "MySQL"
#   target2:
#     name: "target2"
#     services:
#       - name: "SSH"
#         port: 22
#   target3:
#     name: "target2"
#     services:
#       - name: "SSH"
#         port: 22
logger = logging.getLogger(__name__)


class ScenarioArchitectureManager(models.Manager):
    """Manager for ScenarioArchitecture model"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.container_service = DockerService()

    def prepare_scenario(self, blue_team, red_team, template):
        try:
            temp_scenario_dir, flag_mapping = self.prepare_flags(blue_team, template)
            scenario_network, subnet = self.docker_service.create_network()
            session = create_session()

            container = self.container_service.create_game_container(template, session, blue_team, red_team)
            if not container:
                raise ContainerOperationError("Failed to create game container")

            container.flags = flag_mapping.values()
            container.save()

            if not self.container_service.configure_ssh_access(container, blue_team):
                raise ContainerOperationError("Failed to configure SSH access")

            self.docker_service.connect_container_to_network(scenario_network, container)

            return container
        except (ContainerOperationError, DockerOperationError) as e:
            self.stderr.write(self.style.ERROR(f"Container operation failed: {e}"))
        except ValueError as e:
            self.stderr.write(self.style.ERROR(f"Validation error: {e}"))
        except Exception as e:
            logger.exception("Unexpected error in prepare_scenario")
            self.stderr.write(self.style.ERROR(f"Unexpected error: {str(e)}"))

    def prepare_flags(self, team, template):
        # Generate flags for each placeholder
        flag_mapping = {}
        for flag in template.containers_config["flags"]:
            db_flag = Flag.objects.create_flag(flag["id"], flag["points"])
            flag_mapping[flag["placeholder"]] = db_flag

        # Create temporary directory for this team's version
        temp_dir = f"temp/{team.pk}/{template.name}"
        shutil.copytree(template.get_full_path(), temp_dir)

        # Replace placeholders in all files
        for root, _, files in os.walk(temp_dir):
            for file in files:
                filepath = Path(root) / file
                if filepath.is_file():
                    self.replace_placeholders(filepath, flag_mapping)

        return temp_dir, flag_mapping

    def replace_placeholders(self, filepath: Path, flag_mapping):
        try:
            with open(filepath, "rb") as f:
                content = f.read().decode("utf-8", errors="ignore")

            # Only process files that contain flag placeholders
            if "{{FLAG_PLACEHOLDER_" in content:
                for placeholder, flag in flag_mapping.items():
                    content = content.replace(placeholder, flag.value)

                with open(filepath, "w") as f:
                    f.write(content)
        except Exception:
            # Skip problematic files
            pass
