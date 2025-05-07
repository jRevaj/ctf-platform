import logging
import os
import re
import shutil
from pathlib import Path
from typing import Optional

from django.conf import settings

from challenges.models import ChallengeDeployment, ChallengeNetworkConfig
from challenges.models.enums import ContainerStatus
from challenges.models.exceptions import ContainerOperationError, DockerOperationError
from challenges.services import DockerService, ContainerService
from ctf.models import Flag

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

    logger.info(f"Copying template files from {source_path} to {temp_dir}")
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
        self.docker_service = docker_service or DockerService()
        self.container_service = container_service or ContainerService(docker_service=self.docker_service)

    def prepare_challenge(self, session, blue_team) -> Optional[ChallengeDeployment]:
        """Prepare a challenge (single or multi-container) for a blue team"""
        template = session.template
        is_single_container = (bool(template.containers_config) and len(dict(template.containers_config)) == 1)
        logger.info(
            f"Preparing '{template.name}' for blue team {blue_team.id} ({'single' if is_single_container else 'multi'}-container)")
        temp_challenge_dir = create_temp_folder(template)

        try:
            flag_mapping = self.prepare_flags(temp_challenge_dir, blue_team, template)
            deployment = ChallengeDeployment.objects.create(template=template)

            if is_single_container:
                containers = self.prepare_single_container(template, temp_challenge_dir, session, blue_team,
                                                           flag_mapping)
                network = None
            else:
                containers = self.prepare_multi_container(template, temp_challenge_dir, session, blue_team,
                                                          flag_mapping)
                container_map = {container.template_name: container for container in containers}
                network = self.setup_container_networks(template, session.pk, deployment.pk, container_map, containers)

            deployment.containers.set(containers)

            if network:
                if isinstance(network, list):
                    logger.debug(f"Adding {len(network)} networks to deployment")
                    for net in network:
                        deployment.networks.add(net)
                else:
                    deployment.networks.add(network)

            deployment.save()
            return deployment
        except (ContainerOperationError, DockerOperationError, ValueError) as e:
            logger.error(f"Error preparing challenge: {str(e)}")
            if not is_single_container:
                self.docker_service.clean_networks()
            raise e
        except Exception as e:
            logger.exception(f"Unexpected error preparing challenge: {str(e)}")
            if not is_single_container:
                self.docker_service.clean_networks()
            raise e
        finally:
            remove_temp_folder(temp_challenge_dir)

    def prepare_single_container(self, template, temp_dir, session, blue_team, flag_mapping):
        """Prepare a single container challenge"""
        logger.info(f"Creating single container for template {template.name}")
        container = self.container_service.create_game_container(
            template=template,
            temp_dir=temp_dir,
            session=session,
            blue_team=blue_team,
        )

        if not container:
            raise ContainerOperationError("Failed to create game container")

        if self.container_service.docker.check_status(container.docker_id) != ContainerStatus.RUNNING:
            raise DockerOperationError(f"Container {container.name} is not running")

        self.configure_container_ssh(container, blue_team)
        self.configure_container_port(container)
        self.assign_flags_to_container(container, flag_mapping)

        return [container]

    def prepare_multi_container(self, template, temp_dir, session, blue_team, flag_mapping):
        """Prepare a multi-container challenge"""
        logger.info(f"Creating related containers for template {template.name}")
        containers = self.container_service.create_related_containers(
            template, temp_dir, session, blue_team
        )

        if not containers:
            raise ContainerOperationError("Failed to create game containers")

        logger.debug(f"Configuring {len(containers)} containers")
        for container in containers:
            if self.docker_service.check_status(container.docker_id) != ContainerStatus.RUNNING:
                raise DockerOperationError(f"Container {container.name} is not running")

            self.assign_flags_to_container(container, flag_mapping)

            if container.is_entrypoint:
                self.configure_container_ssh(container, blue_team)

            self.configure_container_port(container)

        return containers

    def setup_container_networks(self, template, session_pk, deployment_pk, container_map, containers):
        """Setup networks for containers based on template config or create a default network"""
        logger.info(f"Setting up networks for challenge template {template.name}")
        network_configs = []

        if self._has_network_config(template):
            networks = {}
            network_definitions = self._extract_network_definitions(template.networks_config)

            if network_definitions:
                logger.debug(f"Found {len(network_definitions)} network definitions")

                for network_def in network_definitions:
                    network_name = network_def.get('name')
                    container_names = network_def.get('containers', [])

                    if network_name and container_names:
                        logger.info(f"Creating network '{network_name}' with {len(container_names)} containers")
                        network, subnet = self.docker_service.create_network()
                        networks[network_name] = network

                        db_network = ChallengeNetworkConfig.objects.create(
                            name=f"{network_name}-{session_pk}-{deployment_pk}",
                            subnet=subnet.split('/')[0],
                            template=template,
                            deployment_id=deployment_pk
                        )

                        for container_name in container_names:
                            if container_name in container_map:
                                container = container_map[container_name]
                                logger.debug(f"Connecting container '{container.name}' to network '{network_name}'")
                                self.docker_service.connect_container_to_network(network, container)
                                db_network.containers.add(container)
                            else:
                                logger.warning(f"Container '{container_name}' specified in network config not found")

                        db_network.save()
                        network_configs.append(db_network)

                logger.info(f"Disconnecting non-entrypoint containers from bridge network")
                for container in containers:
                    if not container.is_entrypoint:
                        docker_container = self.docker_service.get_container(container.docker_id)
                        self.docker_service.disconnect_from_bridge(docker_container)

            if network_configs:
                return network_configs
            else:
                logger.warning("No valid network configurations found despite having network config")
                return None
        else:
            logger.info("Creating a single network for all containers")
            challenge_network, subnet = self.container_service.docker.create_network()

            db_network = ChallengeNetworkConfig.objects.create(
                name=f"default-{session_pk}-{deployment_pk}",
                subnet=subnet.split('/')[0],
                template=template,
                deployment_id=deployment_pk
            )

            for container in containers:
                logger.debug(f"Connecting container '{container.name}' to default network")
                self.docker_service.connect_container_to_network(challenge_network, container)
                db_network.containers.add(container)

            for container in containers:
                if not container.is_entrypoint:
                    self.docker_service.disconnect_from_bridge(container)

            db_network.save()
            logger.info(f"Created default network with subnet {subnet}")
            return db_network

    def _extract_network_definitions(self, networks_config):
        """
        Extract network definitions from networks_config regardless of structure.
        Handles various formats of the networks configuration.
        """
        if not networks_config:
            return []

        network_definitions = []

        if isinstance(networks_config, list):
            for item in networks_config:
                if isinstance(item, dict) and 'name' in item and 'containers' in item:
                    network_definitions.append(item)
            return network_definitions

        if isinstance(networks_config, dict):
            if 'name' in networks_config and 'containers' in networks_config:
                return [networks_config]

            for key, value in networks_config.items():
                if isinstance(value, list):
                    valid_networks = []
                    for item in value:
                        if isinstance(item, dict) and 'name' in item and 'containers' in item:
                            valid_networks.append(item)

                    if valid_networks:
                        network_definitions.extend(valid_networks)

                elif isinstance(value, dict):
                    nested_networks = self._extract_network_definitions(value)
                    if nested_networks:
                        network_definitions.extend(nested_networks)

        return network_definitions

    @staticmethod
    def _has_network_config(template):
        """Check if template has any kind of network configuration"""
        return hasattr(template, 'networks_config') and template.networks_config

    def configure_container_ssh(self, container, blue_team):
        """Configure SSH access for a container"""
        logger.debug(f"Configuring SSH for container {container.name}")
        if not self.container_service.configure_ssh_access(container, blue_team):
            raise ContainerOperationError(f"Failed to configure SSH access for container {container.name}")

    def configure_container_port(self, container):
        """Configure port mapping for a container"""
        try:
            container.port = (
                self.docker_service.get_container(container.docker_id)
                .attrs["NetworkSettings"]["Ports"]["22/tcp"][0]["HostPort"]
            )
            container.save(update_fields=['port'])
            logger.debug(f"Container {container.name} port set to {container.port}")
        except (KeyError, IndexError) as e:
            raise ContainerOperationError(f"Failed to get port for container {container.name}: {e}")

    @staticmethod
    def assign_flags_to_container(container, flag_mapping):
        """Assign flags to a container"""
        container_flags = flag_mapping.get(container.template_name, [])

        if not container_flags and len(flag_mapping) == 1:
            container_key = next(iter(flag_mapping.keys()))
            container_flags = flag_mapping.get(container_key, [])

            if container_flags:
                logger.debug(f"Using flags from {container_key} for container {container.name}")
                container.template_name = container_key

        flag_objects = [flag_data["flag"] for flag_data in container_flags]

        for flag in flag_objects:
            flag.container = container
            flag.save(update_fields=['container'])

        container.save()
        logger.debug(f"Assigned {len(flag_objects)} flags to container {container.name}")

    def prepare_flags(self, temp_dir, team, template):
        logger.info(f"Preparing flags for template {template.name}, team {team.id}")
        flag_mapping = {}
        for key, value in template.containers_config.items():
            if "flags" in value:
                container_flags = []
                for flag in value["flags"]:
                    db_flag = Flag.objects.create_flag(team, flag["points"], flag["placeholder"], flag["hint"])
                    container_flags.append({
                        "flag": db_flag,
                        "placeholder": flag["placeholder"]
                    })

                if container_flags:
                    logger.debug(f"Created {len(container_flags)} flags for container {key}")
                    flag_mapping[key] = container_flags

        self._replace_flag_placeholders(temp_dir, flag_mapping)
        return flag_mapping

    def _replace_flag_placeholders(self, temp_dir, flag_mapping):
        """Replace flag placeholders in all files under temp_dir"""
        total_files = 0
        replaced_files = 0

        for root, _, files in os.walk(temp_dir):
            for file in files:
                filepath = Path(root) / file
                total_files += 1
                if filepath.is_file() and self.replace_placeholders(filepath, flag_mapping):
                    replaced_files += 1

        logger.debug(f"Replaced flag placeholders in {replaced_files}/{total_files} files")

    @staticmethod
    def replace_placeholders(filepath: Path, flag_mapping):
        try:
            content = filepath.read_text(encoding='utf-8')

            pattern = r'FLAG_PLACEHOLDER_\d+'
            if not re.search(pattern, content):
                return False

            modified = False
            for container_name, flags_list in flag_mapping.items():
                for flag_data in flags_list:
                    if flag_data["placeholder"] in content:
                        content = content.replace(flag_data["placeholder"], flag_data["flag"].value)
                        modified = True

            if modified:
                filepath.write_text(content, encoding='utf-8')
                return True

            return False
        except Exception as e:
            logger.error(f"Error processing {filepath}: {str(e)}")
            return False
