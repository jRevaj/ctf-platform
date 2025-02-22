import json
import logging
import os
import shutil
from pathlib import Path

from django.conf import settings
from django.db import models

from ctf.management.commands.utils import create_session
from ctf.models import ContainerOperationError, Flag, GameContainer
from ctf.models.exceptions import DockerOperationError
from ctf.services.container_service import ContainerService
from ctf.services.docker_service import DockerService, connect_container_to_network

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

    def __init__(self):
        super().__init__()
        self.docker_service = DockerService()
        self.container_service = ContainerService(docker_service=self.docker_service)

    def prepare_scenario(self, blue_team, red_team, template):
        try:
            temp_scenario_dir, flag_mapping = self.prepare_flags(blue_team, template)
            scenario_network, subnet = self.container_service.docker.create_network()
            session = create_session()

            container = self.container_service.create_game_container(template, session, blue_team, red_team)
            if not container:
                raise ContainerOperationError("Failed to create game container")

            container.flags = flag_mapping.values()
            container.save()

            if not self.container_service.configure_ssh_access(container, blue_team):
                raise ContainerOperationError("Failed to configure SSH access")

            connect_container_to_network(scenario_network, container)

            return container
        except (ContainerOperationError, DockerOperationError) as e:
            raise e
        except ValueError as e:
            raise e
        except Exception as e:
            raise e

    def prepare_flags(self, team, template):
        # Generate flags for each placeholder
        flag_mapping = {}
        logger.info(template.containers_config)
        # TODO: debug and implement flag preparation
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

    @staticmethod
    def replace_placeholders(filepath: Path, flag_mapping):
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


class ScenarioTemplate(models.Model):
    folder = models.CharField(
        max_length=128,
        unique=True,
        null=True,
        help_text="Folder name in game-scenarios directory",
    )
    name = models.CharField(max_length=64)
    title = models.CharField(max_length=256, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    docker_compose = models.TextField(null=True, blank=True)
    containers_config = models.JSONField(default=dict, null=True, blank=True)

    def __str__(self) -> str:
        return self.name

    def get_folder(self) -> str:
        return f"game-scenarios/{self.folder}"

    def get_full_path(self) -> Path:
        return Path(settings.BASE_DIR) / self.get_folder()


class ScenarioNetworkConfig(models.Model):
    template = models.ForeignKey(ScenarioTemplate, on_delete=models.PROTECT)
    subnet = models.GenericIPAddressField()
    used_ips = models.JSONField(default=list)
    containers = models.ManyToManyField(GameContainer, related_name="scenario_network_config")


class ScenarioArchitecture(models.Model):
    template = models.ForeignKey(ScenarioTemplate, on_delete=models.PROTECT)
    containers = models.ManyToManyField(GameContainer, related_name="scenario_architecture")
    network = models.ForeignKey(ScenarioNetworkConfig, on_delete=models.PROTECT)

    objects = ScenarioArchitectureManager()
