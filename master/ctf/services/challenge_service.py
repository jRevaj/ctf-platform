import logging
import os
import re
import shutil
from pathlib import Path

from django.conf import settings

from ctf.management.commands.utils import create_session
from ctf.models import Flag
from ctf.models.enums import ContainerStatus
from ctf.models.exceptions import DockerOperationError, ContainerOperationError
from ctf.services.container_service import ContainerService
from ctf.services.docker_service import DockerService, connect_container_to_network

logger = logging.getLogger(__name__)


def create_temp_folder(template):
    """Create temporary folder for challenge files"""
    temp_dir = f"temp/{template.name}"

    temp_path = Path(settings.BASE_DIR) / temp_dir
    temp_path.parent.mkdir(parents=True, exist_ok=True)

    source_path = template.get_full_template_path()
    if not source_path.exists():
        logger.warning(f"Source path {source_path} does not exist, creating empty temp directory")
        temp_path.mkdir(parents=True, exist_ok=True)
        return temp_dir

    shutil.copytree(source_path, temp_dir)
    return temp_dir


def remove_temp_folder(folder):
    """Remove temp folder"""
    try:
        parent = Path(folder).parent
        logger.info(f"Removing temp folder {parent}")
        shutil.rmtree(Path(settings.BASE_DIR) / parent)
    except Exception as e:
        logger.error(f"Error removing temp folder {folder}: {str(e)}")


class ChallengeService:
    def __init__(self, docker_service=None, container_service=None):
        """
        Initialize with dependency injection to avoid circular imports
        """
        self.docker_service = docker_service or DockerService()
        self.container_service = container_service or ContainerService(docker_service=self.docker_service)

    def prepare_challenge(self, template, blue_team):
        # TODO: implement single container deployment
        temp_challenge_dir = create_temp_folder(template)
        try:
            flag_mapping = self.prepare_flags(temp_challenge_dir, blue_team, template)

            session = create_session()
            containers = self.container_service.create_related_containers(template, temp_challenge_dir, session,
                                                                          blue_team)
            if not containers:
                raise ContainerOperationError("Failed to create game containers")

            challenge_network, subnet = self.container_service.docker.create_network()
            for container in containers:
                if self.container_service.docker.check_status(container.docker_id) != ContainerStatus.RUNNING:
                    raise DockerOperationError("Container is not running")

                container_flags = flag_mapping.get(container.template_name, [])
                flag_objects = [flag_data["flag"] for flag_data in container_flags]
                for flag in flag_objects:
                    flag.container = container
                    flag.save()

                container.save()

                if container.template_name == "target1":
                    if not self.container_service.configure_ssh_access(container, blue_team):
                        raise ContainerOperationError("Failed to configure SSH access")

                # TODO: complex network setups
                connect_container_to_network(challenge_network, container)
                container.port = \
                    self.docker_service.get_container(container.docker_id).attrs["NetworkSettings"]["Ports"]["22/tcp"][
                        0][
                        "HostPort"]
                container.save()

            # TODO: create and return challenge architecture object
            return containers
        except (ContainerOperationError, DockerOperationError, ValueError, Exception) as e:
            self.container_service.docker.clean_networks()
            raise e
        finally:
            remove_temp_folder(temp_challenge_dir)

    def prepare_flags(self, temp_dir, team, template):
        flag_mapping = {}
        for key, value in template.containers_config.items():
            if "flags" in value:
                logger.info(f"Preparing flags for container {key}")
                flag_mapping[key] = []
                for flag in value["flags"]:
                    db_flag = Flag.objects.create_flag(team, flag["points"], flag["placeholder"], flag["hint"])
                    flag_mapping[key].append({
                        "flag": db_flag,
                        "placeholder": flag["placeholder"]
                    })
            else:
                logger.info(f"Container {key} has no flags")

        for root, _, files in os.walk(temp_dir):
            for file in files:
                filepath = Path(root) / file
                if filepath.is_file():
                    success = self.replace_placeholders(filepath, flag_mapping)
                    if not success:
                        logger.error(f"Failed to replace placeholders for file {filepath}")

        return flag_mapping

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
