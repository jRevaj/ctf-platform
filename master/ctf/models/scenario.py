import logging
import os
import re
import shutil
from pathlib import Path

from django.conf import settings
from django.db import models

from ctf.management.commands.utils import create_session
from ctf.models import ContainerOperationError, Flag, GameContainer, ContainerStatus
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


def remove_temp_folder(folder):
    """Remove temp folder"""
    try:
        parent = Path(folder).parent
        logger.info(f"Removing temp folder {parent}")
        shutil.rmtree(Path(settings.BASE_DIR) / parent)
    except Exception as e:
        logger.error(f"Error removing temp folder {folder}: {str(e)}")


class ScenarioArchitectureManager(models.Manager):
    """Manager for ScenarioArchitecture model"""

    def __init__(self):
        super().__init__()
        self.docker_service = DockerService()
        self.container_service = ContainerService(docker_service=self.docker_service)

    def prepare_scenario(self, template, blue_team):
        try:
            temp_scenario_dir, flag_mapping = self.prepare_flags(blue_team, template)
            template.folder = temp_scenario_dir
            template.save()

            session = create_session()
            containers = self.container_service.create_related_containers(template, session, blue_team)
            if not containers:
                raise ContainerOperationError("Failed to create game containers")

            scenario_network, subnet = self.container_service.docker.create_network()
            for container in containers:
                if self.container_service.docker.check_status(container.docker_id) != ContainerStatus.RUNNING:
                    raise DockerOperationError("Container is not running")

                container_flags = flag_mapping.get(container.template_name, [])
                container.flags.set([flag_data["flag"] for flag_data in container_flags])
                container.save()

                if not self.container_service.configure_ssh_access(container, blue_team):
                    raise ContainerOperationError("Failed to configure SSH access")

                connect_container_to_network(scenario_network, container)

            return containers
        except (ContainerOperationError, DockerOperationError, ValueError, Exception) as e:
            self.container_service.docker.clean_networks()
            remove_temp_folder(template.folder)
            raise e

    def prepare_flags(self, team, template):
        flag_mapping = {}
        for key, value in template.containers_config.items():
            if "flags" in value:
                logger.info(f"Preparing flags for container {key}")
                flag_mapping[key] = []
                for flag in value["flags"]:
                    db_flag = Flag.objects.create_flag(flag["points"], flag["placeholder"], flag["hint"])
                    flag_mapping[key].append({
                        "flag": db_flag,
                        "placeholder": flag["placeholder"]
                    })
            else:
                logger.info(f"Container {key} has no flags")

        temp_dir = f"temp/{team.pk}/{template.name}"
        shutil.copytree(template.get_full_template_path(), temp_dir)

        for root, _, files in os.walk(temp_dir):
            for file in files:
                filepath = Path(root) / file
                if filepath.is_file():
                    success = self.replace_placeholders(filepath, flag_mapping)
                    if not success:
                        logger.error(f"Failed to replace placeholders for file {filepath}")

        return temp_dir, flag_mapping

    @staticmethod
    def replace_placeholders(filepath: Path, flag_mapping):
        try:
            content = filepath.read_text(encoding='utf-8')

            pattern = r'FLAG_PLACEHOLDER_\d+'
            if not re.search(pattern, content):
                return True

            modified = False
            for container_name, flags_list in flag_mapping.items():
                # Iterate through all flags for this container
                for flag_data in flags_list:
                    if flag_data["placeholder"] in content:
                        content = content.replace(flag_data["placeholder"], flag_data["flag"].value)
                        modified = True

            if modified:
                filepath.write_text(content, encoding='utf-8')

            return True
        except Exception as e:
            logging.error(f"Error processing {filepath}: {str(e)}")
            return False


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

    def get_template_folder(self) -> str:
        return f"game-scenarios/{self.name}"

    def get_full_template_path(self) -> Path:
        return Path(settings.BASE_DIR) / self.get_template_folder()


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
