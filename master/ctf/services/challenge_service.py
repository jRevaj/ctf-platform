import logging
import os
import re
import shutil
from pathlib import Path
from typing import Optional

from django.conf import settings

from ctf.management.commands.utils import create_session
from ctf.models import Flag, ChallengeArchitecture, ChallengeNetworkConfig
from ctf.models.enums import ContainerStatus
from ctf.models.exceptions import DockerOperationError, ContainerOperationError
from ctf.services.container_service import ContainerService
from ctf.services.docker_service import DockerService

logger = logging.getLogger(__name__)


def create_temp_folder(template):
    """Create temporary folder for challenge files"""
    logger.debug(f"Creating temporary folder for challenge template: {template.name}")
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
        logger.debug(f"Successfully removed temp folder {parent}")
    except Exception as e:
        logger.error(f"Error removing temp folder {folder}: {str(e)}")


class ChallengeService:
    def __init__(self, docker_service=None, container_service=None):
        logger.debug("Initializing ChallengeService")
        self.docker_service = docker_service or DockerService()
        self.container_service = container_service or ContainerService(docker_service=self.docker_service)

    def prepare_challenge(self, template, blue_team) -> Optional[ChallengeArchitecture]:
        """Prepare a challenge (single or multi-container) for a blue team"""
        logger.info(f"Preparing challenge '{template.name}' for blue team {blue_team.id}")
        is_single_container = (bool(template.containers_config) and len(dict(template.containers_config)) == 1)
        logger.debug(f"Challenge type: {'single-container' if is_single_container else 'multi-container'}")
        temp_challenge_dir = create_temp_folder(template)

        try:
            logger.debug(f"Preparing flags for the challenge")
            flag_mapping = self.prepare_flags(temp_challenge_dir, blue_team, template)
            logger.debug(f"Creating ChallengeArchitecture record")
            architecture = ChallengeArchitecture.objects.create(template=template)
            session = create_session()

            if is_single_container:
                logger.info(f"Preparing single container challenge")
                containers = self.prepare_single_container(template, temp_challenge_dir, session, blue_team,
                                                           flag_mapping)
                network = None
            else:
                logger.info(f"Preparing multi-container challenge")
                containers = self.prepare_multi_container(template, temp_challenge_dir, session, blue_team,
                                                          flag_mapping)
                container_map = {container.template_name: container for container in containers}
                logger.info(f"Setting up container networks")
                network = self.setup_container_networks(template, container_map, containers)

            logger.debug(f"Associating containers with architecture")
            architecture.containers.set(containers)

            if network:
                if isinstance(network, list):
                    logger.debug(f"Adding {len(network)} networks to architecture")
                    for net in network:
                        architecture.networks.add(net)
                else:
                    logger.debug(f"Adding network {network.name} to architecture")
                    architecture.networks.add(network)

            architecture.save()
            logger.info(f"Successfully prepared challenge '{template.name}' for blue team {blue_team.id}")
            return architecture
        except (ContainerOperationError, DockerOperationError, ValueError) as e:
            logger.error(f"Error preparing challenge: {str(e)}")
            if not is_single_container:
                logger.info("Cleaning up networks due to error")
                self.docker_service.clean_networks()
            raise e
        except Exception as e:
            logger.exception(f"Unexpected error preparing challenge: {str(e)}")
            if not is_single_container:
                logger.info("Cleaning up networks due to error")
                self.docker_service.clean_networks()
            raise e
        finally:
            remove_temp_folder(temp_challenge_dir)

    def prepare_single_container(self, template, temp_dir, session, blue_team, flag_mapping):
        """Prepare a single container challenge"""
        logger.debug(f"Creating single game container for template {template.name}")
        container = self.container_service.create_game_container(
            template=template,
            temp_dir=temp_dir,
            session=session,
            blue_team=blue_team,
        )

        if not container:
            logger.error("Failed to create game container")
            raise ContainerOperationError("Failed to create game container")

        logger.debug(f"Checking status of container {container.name} ({container.docker_id})")
        if self.container_service.docker.check_status(container.docker_id) != ContainerStatus.RUNNING:
            logger.error(f"Container {container.name} is not running")
            raise DockerOperationError("Container is not running")

        logger.debug(f"Configuring SSH access for container {container.name}")
        self.configure_container_ssh(container, blue_team)
        logger.debug(f"Configuring port mapping for container {container.name}")
        self.configure_container_port(container)
        logger.debug(f"Assigning flags to container {container.name}")
        self.assign_flags_to_container(container, flag_mapping)

        logger.info(f"Successfully prepared single container {container.name}")
        return [container]

    def prepare_multi_container(self, template, temp_dir, session, blue_team, flag_mapping):
        """Prepare a multi-container challenge"""
        logger.debug(f"Creating related containers for template {template.name}")
        containers = self.container_service.create_related_containers(
            template, temp_dir, session, blue_team
        )

        if not containers:
            logger.error("Failed to create game containers")
            raise ContainerOperationError("Failed to create game containers")

        logger.debug(f"Created {len(containers)} containers, configuring each one")
        for container in containers:
            logger.debug(f"Checking status of container {container.name} ({container.docker_id})")
            if self.docker_service.check_status(container.docker_id) != ContainerStatus.RUNNING:
                logger.error(f"Container {container.name} is not running")
                raise DockerOperationError(f"Container {container.name} is not running")

            logger.debug(f"Assigning flags to container {container.name}")
            self.assign_flags_to_container(container, flag_mapping)

            if container.is_entrypoint:
                logger.debug(f"Configuring SSH access for entrypoint container {container.name}")
                self.configure_container_ssh(container, blue_team)

            logger.debug(f"Configuring port mapping for container {container.name}")
            self.configure_container_port(container)

        logger.info(f"Successfully prepared {len(containers)} containers")
        return containers

    def setup_container_networks(self, template, container_map, containers):
        """Setup networks for containers based on template config or create a default network"""
        logger.debug(f"Setting up networks for challenge template {template.name}")
        network_configs = []

        if self._has_network_config(template):
            logger.info(f"Using template-defined network configuration")
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
                            name=network_name,
                            subnet=subnet.split('/')[0],
                            template=template
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
                        logger.debug(f"Network '{network_name}' setup complete")

                logger.info(f"Disconnecting non-entrypoint containers from bridge network to enforce network isolation")
                for container in containers:
                    if not container.is_entrypoint:
                        logger.info(f"Disconnecting container {container.name} from bridge network")
                        self.docker_service.disconnect_from_bridge(container)

            if network_configs:
                logger.info(f"Created {len(network_configs)} networks")
                return network_configs
            else:
                logger.warning("No valid network configurations found despite having network config")
                return None
        else:
            logger.info("No network configuration found, creating a single network for all containers")
            challenge_network, subnet = self.container_service.docker.create_network()

            db_network = ChallengeNetworkConfig.objects.create(
                name="default",
                subnet=subnet.split('/')[0],
                template=template,
            )

            for container in containers:
                logger.debug(f"Connecting container '{container.name}' to default network")
                self.docker_service.connect_container_to_network(challenge_network, container)
                db_network.containers.add(container)

            logger.info(f"Disconnecting non-entrypoint containers from bridge network")
            for container in containers:
                if not container.is_entrypoint:
                    logger.info(f"Disconnecting container {container.name} from bridge network")
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
            logger.debug("Empty networks_config")
            return []

        network_definitions = []

        if isinstance(networks_config, list):
            logger.debug("networks_config is a direct list of network definitions")
            for item in networks_config:
                if isinstance(item, dict) and 'name' in item and 'containers' in item:
                    network_definitions.append(item)
            return network_definitions

        if isinstance(networks_config, dict):
            if 'name' in networks_config and 'containers' in networks_config:
                logger.debug("networks_config is a single network definition")
                return [networks_config]

            for key, value in networks_config.items():
                logger.debug(f"Checking network definitions under key '{key}'")

                if isinstance(value, list):
                    valid_networks = []
                    for item in value:
                        if isinstance(item, dict) and 'name' in item and 'containers' in item:
                            valid_networks.append(item)

                    if valid_networks:
                        logger.debug(f"Found {len(valid_networks)} network definitions under '{key}'")
                        network_definitions.extend(valid_networks)

                elif isinstance(value, dict):
                    nested_networks = self._extract_network_definitions(value)
                    if nested_networks:
                        network_definitions.extend(nested_networks)

        logger.debug(f"Extracted a total of {len(network_definitions)} network definitions")
        return network_definitions

    @staticmethod
    def _has_network_config(template):
        """Check if template has any kind of network configuration"""
        logger.debug(f"Checking if template {template.name} has network configuration")
        if hasattr(template, 'networks_config') and template.networks_config:
            logger.debug(f"Found networks_config for {template.name}")
            return True

        logger.debug("No network configuration found")
        return False

    def configure_container_ssh(self, container, blue_team):
        """Configure SSH access for a container"""
        logger.debug(f"Configuring SSH access for container {container.name}")
        if not self.container_service.configure_ssh_access(container, blue_team):
            logger.error(f"Failed to configure SSH access for container {container.name}")
            raise ContainerOperationError(f"Failed to configure SSH access for container {container.name}")
        logger.info(f"Successfully configured SSH access for container {container.name}")

    def configure_container_port(self, container):
        """Configure port mapping for a container"""
        logger.debug(f"Configuring port mapping for container {container.name}")
        try:
            container.port = (
                self.docker_service.get_container(container.docker_id)
                .attrs["NetworkSettings"]["Ports"]["22/tcp"][0]["HostPort"]
            )
            container.save()
            logger.info(f"Container {container.name} port set to {container.port}")
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to get port for container {container.name}: {e}")
            raise ContainerOperationError(f"Failed to get port for container {container.name}: {e}")

    @staticmethod
    def assign_flags_to_container(container, flag_mapping):
        """Assign flags to a container"""
        logger.debug(f"Assigning flags to container {container.name} (template: {container.template_name})")
        container_flags = flag_mapping.get(container.template_name, [])

        if not container_flags and len(flag_mapping) == 1:
            container_key = next(iter(flag_mapping.keys()))
            container_flags = flag_mapping.get(container_key, [])

            if container_flags:
                logger.debug(f"Using flags from {container_key} for container {container.name}")
                container.template_name = container_key

        flag_objects = [flag_data["flag"] for flag_data in container_flags]
        logger.debug(f"Associating {len(flag_objects)} flags with container {container.name}")

        for flag in flag_objects:
            flag.container = container
            flag.save()

        container.save()
        logger.info(f"Successfully assigned {len(flag_objects)} flags to container {container.name}")

    def prepare_flags(self, temp_dir, team, template):
        logger.info(f"Preparing flags for template {template.name}, team {team.id}")
        flag_mapping = {}
        for key, value in template.containers_config.items():
            if "flags" in value:
                logger.info(f"Preparing flags for container {key}")
                flag_mapping[key] = []
                for flag in value["flags"]:
                    logger.debug(f"Creating flag with points {flag['points']} and placeholder {flag['placeholder']}")
                    db_flag = Flag.objects.create_flag(team, flag["points"], flag["placeholder"], flag["hint"])
                    flag_mapping[key].append({
                        "flag": db_flag,
                        "placeholder": flag["placeholder"]
                    })
            else:
                logger.info(f"Container {key} has no flags")

        logger.debug(f"Replacing flag placeholders in files under {temp_dir}")
        for root, _, files in os.walk(temp_dir):
            for file in files:
                filepath = Path(root) / file
                if filepath.is_file():
                    logger.debug(f"Processing file for flag replacement: {filepath}")
                    success = self.replace_placeholders(filepath, flag_mapping)
                    if not success:
                        logger.error(f"Failed to replace placeholders for file {filepath}")

        logger.info(f"Flag preparation complete with {sum(len(flags) for flags in flag_mapping.values())} flags")
        return flag_mapping

    @staticmethod
    def replace_placeholders(filepath: Path, flag_mapping):
        try:
            logger.debug(f"Replacing flag placeholders in {filepath}")
            content = filepath.read_text(encoding='utf-8')

            pattern = r'FLAG_PLACEHOLDER_\d+'
            if not re.search(pattern, content):
                logger.debug(f"No flag placeholders found in {filepath}")
                return True

            modified = False
            for container_name, flags_list in flag_mapping.items():
                for flag_data in flags_list:
                    if flag_data["placeholder"] in content:
                        logger.debug(f"Replacing placeholder {flag_data['placeholder']} in {filepath}")
                        content = content.replace(flag_data["placeholder"], flag_data["flag"].value)
                        modified = True

            if modified:
                logger.debug(f"Writing updated content to {filepath}")
                filepath.write_text(content, encoding='utf-8')
                logger.info(f"Successfully replaced flag placeholders in {filepath}")

            return True
        except Exception as e:
            logger.error(f"Error processing {filepath}: {str(e)}")
            return False
