import logging
import socket
from typing import Optional, Dict

import docker
from docker.errors import APIError, NotFound
from docker.models.containers import Container
from docker.models.networks import Network
from docker.types import IPAMPool, IPAMConfig

from challenges.models.constants import DockerConstants
from challenges.models.enums import ContainerStatus
from challenges.models.exceptions import DockerOperationError, ContainerNotFoundError

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

    @staticmethod
    def execute_command(container: Container, command: list[str], privileged: bool = False) -> tuple[int, str]:
        """Execute a command in a container"""
        try:
            result = container.exec_run(command, privileged=privileged)

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
        """Remove all docker networks"""
        try:
            logger.info("Removing all docker networks")
            self.client.networks.prune()
        except APIError as e:
            logger.error(f"Failed to remove network: {e}")
        except Exception as e:
            logger.error(f"Failed to remove network: {e}")

    @staticmethod
    def connect_container_to_network(network, container) -> bool:
        try:
            network.connect(container.docker_id)
            return True
        except Exception as e:
            logger.error(f"Failed to add container {container.docker_id} to network {network.name}: {e}")
            return False

    @staticmethod
    def disconnect_container_from_network(network: Network, container: Container) -> bool:
        try:
            network.disconnect(container)
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect container {container.name} from network {network.name}: {e}")
            return False

    @staticmethod
    def remove_network(network: Network) -> bool:
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

    def disconnect_from_bridge(self, container: Container) -> bool:
        """Disconnect a container from the default bridge network"""
        try:
            bridge = self.get_bridge_network()
            if bridge:
                bridge.disconnect(container)
                logger.info(f"Container {container.name} disconnected from bridge network")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to disconnect container {container.name} from bridge network: {e}")
            return False

    def check_active_ssh_sessions(self, container_id: str) -> list:
        """Check if there are any active SSH sessions in the container and return session IDs
        
        Returns a list of session IDs for active SSH connections, or an empty list if none.
        This method tries multiple approaches to support different Linux distributions
        including Ubuntu, Alpine, and other common distros.
        
        The session IDs are designed to be stable across multiple checks so that
        the same connection is identified with the same ID in subsequent checks.
        """
        try:
            logger.debug(f"Checking active SSH sessions for container {container_id}")
            container = self.get_container(container_id)
            if not container or container.status != "running":
                logger.warning(f"Container {container_id} not running")
                return []

            # Method 1: Look for child sshd processes that indicate client connections
            # This pattern explicitly excludes the main sshd daemon
            try:
                # Get both PID and connection details for stability
                result = container.exec_run(
                    ["sh", "-c", "ps aux | grep -E 'sshd: [a-zA-Z0-9]+@' | grep -v grep"],
                    privileged=True
                )
                if result.exit_code == 0 and result.output.strip():
                    output = result.output.decode('utf-8').strip()
                    # Create more stable IDs that include the connection details
                    session_ids = []
                    for line in output.split('\n'):
                        if not line.strip():
                            continue
                        # Extract PID (usually 2nd column in ps output)
                        parts = line.split()
                        if len(parts) > 1 and parts[1].isdigit():
                            # Hash the whole line to create a stable ID
                            connection_hash = hash(line) % 10000000
                            session_ids.append(f"ssh-pid-{parts[1]}-{connection_hash}")

                    if session_ids:
                        logger.debug(f"Found SSH sessions with stable IDs: {session_ids}")
                        return session_ids
            except Exception as e:
                logger.error(f"Error in method 1 (ps): {e}")

            # Method 2: Check established connections on port 22 using netstat
            # Get actual IP:port details for stable session IDs
            try:
                result = container.exec_run(
                    ["sh", "-c", "netstat -tn 2>/dev/null | grep ':22' | grep 'ESTABLISHED'"],
                    privileged=True
                )
                if result.exit_code == 0 and result.output.strip():
                    output = result.output.decode('utf-8').strip()
                    session_ids = []

                    for line in output.split('\n'):
                        if not line.strip():
                            continue
                        # Create a hash from the connection details to ensure stable IDs
                        connection_hash = hash(line) % 10000000
                        session_ids.append(f"ssh-net-{connection_hash}")

                    if session_ids:
                        logger.debug(f"Found {len(session_ids)} SSH connections with netstat")
                        return session_ids
            except Exception as e:
                logger.error(f"Error in method 2 (netstat): {e}")

            # Method 3: Try with ss command (newer alternative to netstat in some distros)
            try:
                result = container.exec_run(
                    ["sh", "-c", "command -v ss >/dev/null 2>&1 && ss -tn | grep ':22' | grep 'ESTABLISHED'"],
                    privileged=True
                )
                if result.exit_code == 0 and result.output.strip():
                    output = result.output.decode('utf-8').strip()
                    session_ids = []

                    for line in output.split('\n'):
                        if not line.strip():
                            continue
                        # Create a hash from the connection details to ensure stable IDs
                        connection_hash = hash(line) % 10000000
                        session_ids.append(f"ssh-ss-{connection_hash}")

                    if session_ids:
                        logger.debug(f"Found {len(session_ids)} SSH connections with ss command")
                        return session_ids
            except Exception as e:
                logger.error(f"Error in method 3 (ss): {e}")

            # Method 4: Check for established TCP connections on port 22 in /proc/net/tcp
            # 0016 is port 22 in hex, 01 indicates ESTABLISHED state
            try:
                # First verify there's an actual remote connection by checking the source IP isn't localhost
                # This avoids counting internal connections from the daemon itself
                result = container.exec_run(
                    ["sh", "-c", "cat /proc/net/tcp 2>/dev/null | grep ':0016' | grep ' 01 ' | grep -v '0100007F'"],
                    privileged=True
                )
                if result.exit_code == 0 and result.output.strip():
                    output = result.output.decode('utf-8').strip()

                    # Double-check with netstat/ss to confirm these are really external connections
                    verify_result = container.exec_run(
                        ["sh", "-c",
                         "command -v netstat >/dev/null && netstat -tn | grep ':22' | grep 'ESTABLISHED' | grep -v '127.0.0.1' || echo ''"],
                        privileged=True
                    )

                    if verify_result.exit_code == 0 and verify_result.output.strip():
                        session_ids = []
                        for line in output.split('\n'):
                            if not line.strip():
                                continue
                            # Extract remote addr field for stable hash
                            parts = line.split()
                            if len(parts) > 2:
                                remote_addr = parts[2]
                                session_ids.append(f"ssh-proc-{remote_addr}")

                        if session_ids:
                            logger.debug(f"Found {len(session_ids)} verified SSH connections via /proc/net/tcp")
                            return session_ids
                    else:
                        logger.debug(f"Found potential SSH connections in /proc/net/tcp but verification failed")
            except Exception as e:
                logger.error(f"Error in method 4 (/proc/net/tcp): {e}")

            # Method 5: Look specifically for client connections by checking for username pattern
            # This avoids detecting the main sshd process
            try:
                result = container.exec_run(
                    ["sh", "-c", "ps aux | grep -E 'sshd: .+@' | grep -v grep"],
                    privileged=True
                )
                if result.exit_code == 0 and result.output.strip():
                    output = result.output.decode('utf-8').strip()
                    session_ids = []

                    for line in output.split('\n'):
                        if not line.strip():
                            continue
                        # Create a stable ID based on the username and connection details
                        connection_hash = hash(line) % 10000000

                        # Try to extract the username pattern for more stable ID
                        import re
                        match = re.search(r'sshd: ([^@]+)@', line)
                        username = match.group(1) if match else f"user-{connection_hash}"

                        session_ids.append(f"ssh-user-{username}-{connection_hash}")

                    if session_ids:
                        logger.debug(f"Found {len(session_ids)} client SSH connections via ps")
                        return session_ids
            except Exception as e:
                logger.error(f"Error in method 5 (ps grep): {e}")

            # Method 6: Last resort - use 'who' command to check logged in users
            try:
                result = container.exec_run(
                    ["who"],
                    privileged=True
                )
                if result.exit_code == 0 and result.output.strip():
                    output = result.output.decode('utf-8')
                    session_ids = []

                    for line in output.split('\n'):
                        if not line.strip():
                            continue
                        # Extract username and PTY for stable connection ID
                        parts = line.split()
                        if len(parts) >= 2:
                            username = parts[0]
                            pts = parts[1]
                            session_ids.append(f"ssh-who-{username}-{pts}")

                    if session_ids:
                        logger.debug(f"Found {len(session_ids)} users logged in with 'who' command")
                        return session_ids
            except Exception as e:
                logger.error(f"Error in method 6 (who): {e}")

            # No active SSH sessions found
            logger.debug(f"No active SSH sessions found for container {container_id}")
            return []
        except Exception as e:
            logger.error(f"Failed to check SSH sessions for container {container_id}: {e}")
            # Return empty list on error instead of error messages that could be mistaken for session IDs
            return []
