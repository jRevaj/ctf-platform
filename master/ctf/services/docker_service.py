import docker
import logging
from typing import Tuple, Optional
from docker.models.containers import Container
from docker.models.images import Image

from ctf.models.container import GameContainer
from ctf.models.constants import DockerConstants
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

    def build_image(self, template_path: str, image_tag: str) -> Tuple[Image, list]:
        """Build a Docker image from template"""
        try:
            return self.client.images.build(path=template_path, tag=image_tag, rm=True)
        except Exception as e:
            logger.error(f"Failed to build image {image_tag}: {e}")
            raise

    def create_container(self, image_tag: str, container_name: str) -> Container:
        """Create and start a new Docker container"""
        try:
            return self.client.containers.run(image=image_tag, name=container_name, detach=True, ports={DockerConstants.SSH_PORT: None})
        except Exception as e:
            logger.error(f"Failed to create container {container_name}: {e}")
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
        except docker.errors.NotFound:
            raise ContainerNotFoundError(f"Container {container_id} not found")
        except Exception as e:
            logger.error(f"Failed to get container {container_id}: {e}")
            raise DockerOperationError(f"Failed to get container: {e}")

    @staticmethod
    def get_container_port(container: Container, port: str) -> Optional[str]:
        """Get published port mapping"""
        try:
            port_info = container.attrs["NetworkSettings"]["Ports"][port][0]
            return port_info["HostPort"]
        except Exception as e:
            logger.error(f"Failed to get port mapping for container {container.id}: {e}")
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

    # def deploy_flag(self, container: GameContainer, flag: Flag) -> bool:
    #     """Deploy a flag to a container"""
    #     try:
    #         create_file_with_flag_cmd = ["sh", "-c", f"echo '{flag.value}' > {DockerConstants.FLAGS_CONTAINER_PATH}/flag"]
    #         self.execute_command(container, create_file_with_flag_cmd)
    #         set_permissions_cmd = ["chmod", "000", f"{DockerConstants.FLAGS_CONTAINER_PATH}/flag"]
    #         self.execute_command(container, set_permissions_cmd)

    #         verify_file_cmd = ["ls", "-l", f"{DockerConstants.FLAGS_CONTAINER_PATH}/flag"]
    #         self.execute_command(container, verify_file_cmd)

    #         return True
    #     except Exception as e:
    #         logger.error(f"Failed to deploy flag {flag.value} to container {container.name}: {e}")
    #         return False

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

            for i in range(0, 255):
                subnet = f"172.{i}.0.0/16"
                if subnet not in used_subnets:
                    logger.info(f"Found available subnet: {subnet}")
                    return subnet

            raise DockerOperationError("No available subnet found in any range")

        except Exception as e:
            logger.error(f"Error while finding available subnet: {e}")
            raise DockerOperationError(f"Failed to find available subnet: {e}")

    def create_network(self, subnet: str) -> bool:
        """Create a new Docker network"""
        try:
            subnet = self.get_available_subnet()
            network = self.client.networks.create(name=subnet, driver="bridge", ipam={"Subnet": subnet})
            return network, subnet
        except Exception as e:
            logger.error(f"Failed to create network {subnet}: {e}")
            return False

    def connect_container_to_network(self, network, container) -> bool:
        try:
            network.connect(container.docker_id)
            return True
        except Exception as e:
            logger.error(f"Failed to add container {container.docker_id} to network {network.name}: {e}")
            return False

    def disconnect_container_from_network(self, network, container) -> bool:
        try:
            network.disconnect(container.docker_id)
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect container {container.docker_id} from network {network.name}: {e}")
            return False

    def remove_network(self, network) -> bool:
        try:
            network.remove()
            return True
        except Exception as e:
            logger.error(f"Failed to remove network {network.name}: {e}")
            return False
