import logging
from typing import Optional, Dict

import docker
from docker.errors import APIError, NotFound
from docker.models.containers import Container
from docker.models.networks import Network
from docker.types import IPAMPool, IPAMConfig

from ctf.models.constants import DockerConstants
from ctf.models.container import GameContainer
from ctf.models.enums import ContainerStatus
from ctf.models.exceptions import ContainerNotFoundError, DockerOperationError

logger = logging.getLogger(__name__)


class DockerService:
    """Handles all low-level Docker operations"""

    def __init__(self):
        try:
            self.client = docker.from_env()
            self.client.ping()
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise RuntimeError(f"Failed to connect to Docker: {e}")

    def build_image(self, template_path: str, image_tag: str):
        """Build a Docker image from template"""
        try:
            logger.info(f"Building image {image_tag} from template {template_path}")
            return self.client.images.build(path=template_path, tag=image_tag, rm=True)
        except Exception as e:
            logger.error(f"Failed to build image {image_tag}: {e}")
            raise

    def create_container(self, container_name: str, image_tag: str, port: int = None) -> Container:
        """Create and start a new Docker container"""
        try:
            if port:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.bind(('0.0.0.0', port))
                except (socket.error, OSError) as e:
                    logger.error(f"Port {port} is not available for binding: {e}")
                    raise DockerOperationError(f"Port {port} is not available: {e}")

            container = self.client.containers.run(
                image=image_tag,
                name=container_name,
                detach=True,
                ports={DockerConstants.SSH_PORT: None} if not port else {DockerConstants.SSH_PORT: port},
            )

            if port:
                container.reload()
                actual_port = self.get_container_port(container, DockerConstants.SSH_PORT)
                if actual_port and int(actual_port) != port:
                    logger.warning(f"Container was assigned port {actual_port} instead of requested {port}")

            return container
        except DockerOperationError:
            raise
        except Exception as e:
            logger.error(f"Failed to create container {container_name}: {e}")
            if "Ports are not available" in str(e):
                raise DockerOperationError(f"Port binding failed, port may be in use: {e}")
            raise DockerOperationError(f"Failed to create container: {e}")

    def remove_container(self, container_id: str, force: bool = False) -> bool:
        """Remove a Docker container"""
        try:
            container = self.get_container(container_id)
            if container:
                container.remove(v=True, force=force)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove container {container_id}: {e}")
            return False

    def get_container(self, container_id: str) -> Optional[Container]:
        """Get container by ID"""
        try:
            return self.client.containers.get(container_id)
        except NotFound:
            raise ContainerNotFoundError(f"Container {container_id} not found")
        except Exception as e:
            logger.error(f"Failed to get container {container_id}: {e}")
            raise DockerOperationError(f"Failed to get container: {e}")

    @staticmethod
    def get_container_port(container: Container, port: str) -> Optional[str]:
        """Get published port mapping"""
        try:
            container.reload()
            ports = container.attrs["NetworkSettings"]["Ports"]

            if '/tcp' not in port:
                port = f"{port}/tcp"

            if port not in ports or not ports[port]:
                logger.warning(f"No port mapping for {port} in container {container.id}")
                return None

            port_info = ports[port][0]
            return port_info["HostPort"]
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to get port mapping for container {container.id} - '{port}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting port for container {container.id}: {e}")
            return None

    def list_all_containers(self) -> list[Container]:
        """
        List all Docker containers.

        Returns:
            List[Container]: List of all Docker containers
        """
        try:
            return self.client.containers.list(all=True)
        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            return []

    def execute_command(self, container: GameContainer, command: list[str]) -> tuple[int, str]:
        """Execute a command in a container"""
        try:
            docker_container = self.get_container(container.docker_id)
            result = docker_container.exec_run(command, privileged=True)

            if result.exit_code != 0:
                raise DockerOperationError(f"Failed to execute command: {result.output.decode('utf-8')}")

            return result.exit_code, result.output.decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to execute command in container {container.docker_id}: {e}")
            return -1, str(e)

    def start_container(self, container_id: str) -> bool:
        """Start a Docker container"""
        try:
            container = self.get_container(container_id)
            if container and container.status != "running":
                container.start()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to start container {container_id}: {e}")
            return False

    def stop_container(self, container_id: str) -> bool:
        """Stop a Docker container"""
        try:
            container = self.get_container(container_id)
            if container and container.status == "running":
                container.stop()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to stop container {container_id}: {e}")
            return False

    def check_status(self, container_docker_id: str) -> ContainerStatus | None:
        """Check the status of given container"""
        try:
            return ContainerStatus(self.client.containers.get(container_docker_id).status)
        except (NotFound, APIError) as e:
            logger.error(f"Failed to check status of container: {e}")
            return None

    def prune_images(self, dangling: bool = True) -> Dict | None:
        """Prune unused or dangling images"""
        try:
            logger.info("Pruning unused or dangling images")
            return self.client.images.prune(filters={"dangling": dangling})
        except APIError as e:
            logger.error(f"Failed to prune images: {e}")
            return None

    def list_networks(self) -> list:
        """List all Docker networks"""
        try:
            return self.client.networks.list()
        except Exception as e:
            logger.error(f"Failed to list networks: {e}")
            return []

    def get_available_subnet(self) -> str:
        """Find an available subnet for new network"""
        try:
            used_subnets = []
            for network in self.list_networks():
                if network.attrs.get("IPAM") and network.attrs["IPAM"].get("Config"):
                    for config in network.attrs["IPAM"]["Config"]:
                        if "Subnet" in config:
                            used_subnets.append(config["Subnet"])

            logger.debug(f"Used subnets: {used_subnets}")

            for i in range(1, 255):
                subnet = f"172.{i}.0.0/16"
                if subnet not in used_subnets:
                    logger.info(f"Found available subnet: {subnet}")
                    return subnet

            raise DockerOperationError("No available subnet found in any range")

        except Exception as e:
            logger.error(f"Error while finding available subnet: {e}")
            raise DockerOperationError(f"Failed to find available subnet: {e}")

    def create_network(self) -> bool | tuple[Network, str]:
        """Create a new Docker network"""
        try:
            subnet = self.get_available_subnet()
            ipam_config = IPAMConfig(pool_configs=[IPAMPool(subnet=subnet)])
            network = self.client.networks.create(name=f"{DockerConstants.CONTAINER_PREFIX}{subnet}", driver="bridge",
                                                  ipam=ipam_config)
            return network, subnet
        except Exception as e:
            logger.error(f"Failed to create network: {e}")
            return False

    def clean_networks(self):
        """Clean up unused networks"""
        try:
            logger.info("Cleaning up unused networks")
            self.client.networks.prune()
        except APIError as e:
            logger.error(f"Failed to clean up network: {e}")
        except Exception as e:
            logger.error(f"Failed to clean up network: {e}")

    @staticmethod
    def connect_container_to_network(network, container) -> bool:
        try:
            network.connect(container.docker_id)
            return True
        except Exception as e:
            logger.error(f"Failed to add container {container.docker_id} to network {network.name}: {e}")
            return False

    @staticmethod
    def disconnect_container_from_network(network, container) -> bool:
        try:
            network.disconnect(container.docker_id)
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect container {container.docker_id} from network {network.name}: {e}")
            return False

    @staticmethod
    def remove_network(network) -> bool:
        try:
            network.remove()
            return True
        except Exception as e:
            logger.error(f"Failed to remove network {network.name}: {e}")
            return False

    def get_bridge_network(self) -> Optional[Network]:
        """Get the default bridge network"""
        try:
            return self.client.networks.get("bridge")
        except Exception as e:
            logger.error(f"Failed to get bridge network: {e}")
            return None

    def disconnect_from_bridge(self, container) -> bool:
        """Disconnect a container from the default bridge network"""
        try:
            bridge = self.get_bridge_network()
            if bridge:
                bridge.disconnect(container.docker_id)
                logger.info(f"Container {container.name} disconnected from bridge network")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to disconnect container {container.name} from bridge network: {e}")
            return False
