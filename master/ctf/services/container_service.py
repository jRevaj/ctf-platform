import logging
from pathlib import Path
from typing import Optional

from accounts.models import Team
from ctf.models import GameContainer, GameSession
from ctf.models.constants import DockerConstants
from ctf.models.enums import ContainerStatus
from ctf.models.exceptions import ContainerOperationError
from ctf.services.docker_service import DockerService

logger = logging.getLogger(__name__)


class ContainerService:
    """Business logic for container operations"""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ContainerService, cls).__new__(cls)
            cls._instance.docker = kwargs.get('docker_service') or DockerService()
        return cls._instance

    def create_related_containers(self, template, temp_dir, session, blue_team):
        """Batch create related containers"""
        try:
            containers = []
            template_path = Path(temp_dir) if temp_dir else template.get_full_template_path()
            for filepath in template_path.rglob("*"):
                if filepath.is_file():
                    if filepath.name == 'Dockerfile' or filepath.name.startswith('Dockerfile.'):
                        container = self.create_game_container(template, temp_dir, session, blue_team, filepath)
                        if container:
                            containers.append(container)
                        else:
                            logger.error(f"Failed to create container from {filepath}, skipping")

            logger.info(f"Created {len(containers)} related containers: {containers}")

            if not containers:
                raise ContainerOperationError("Failed to create any containers")

            return containers
        except ContainerOperationError as e:
            logger.error(f"Error batch creating containers: {e}")
            return []
        except Exception as e:
            logger.error(f"Error batch creating containers: {e}")
            return []

    def create_game_container(self, template, temp_dir, session, blue_team, path="") -> Optional[GameContainer]:
        """Create a new game container from template"""
        try:
            logger.info(f"Creating new game container {path if path else temp_dir}")

            if path:
                template_container_path = Path(path)
                container_name = template_container_path.parent.name
            else:
                container_name = Path(temp_dir).name if temp_dir else template.name

            is_entrypoint = False
            if template.containers_config and container_name in template.containers_config:
                container_config = template.containers_config.get(container_name, {})
                is_entrypoint = container_config.get('is_entrypoint', False)
                logger.debug(f"Container {container_name} is_entrypoint set to {is_entrypoint} from template config")

            return GameContainer.objects.create_with_docker(
                template=template,
                temp_dir=temp_dir,
                session=session,
                blue_team=blue_team,
                docker_service=self.docker,
                path=path,
                is_entrypoint=is_entrypoint
            )
        except Exception as e:
            logger.error(f"Failed to create game container: {e}")
            return None

    def swap_ssh_access(self, container: GameContainer, new_team: Team) -> bool:
        """Swap SSH access for the given container to the new team"""
        try:
            self.clean_ssh_access(container)
            self.configure_ssh_access(container, new_team)
            return True
        except Exception as e:
            logger.error(f"Failed to swap SSH access for container {container.docker_id}: {e}")
            return False

    def clean_ssh_access(self, container: GameContainer) -> bool:
        """Clean up SSH access for the given container"""
        try:
            docker_container = self.docker.get_container(container.docker_id)
            if not docker_container:
                logger.warning(f"Container {container.name} ({container.docker_id}) not found")
                return False

            docker_container.exec_run(
                [
                    "sh",
                    "-c",
                    "rm -rf /home/ctf-user/.ssh && rm -rf /home/ctf-user/.ssh/authorized_keys"
                ]
            )

            logger.info(f"SSH access cleaned up for container {container.docker_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to clean up SSH access for container {container.docker_id}: {e}")
            return False

    def configure_ssh_access(self, container: GameContainer, team: Team) -> bool:
        """Configure SSH access for the given container and team"""
        try:
            logger.info(f"Configuring SSH access for {team.name} container {container.name}")
            docker_container = self.docker.get_container(container.docker_id)
            if not docker_container:
                return False

            ssh_keys = [user.ssh_public_key for user in team.users.all() if user.ssh_public_key]

            if not ssh_keys:
                logger.warning(f"No SSH keys found for team {team.id}")
                return False

            authorized_keys = "\n".join(ssh_keys)
            docker_container.exec_run(
                [
                    "sh",
                    "-c",
                    f'mkdir -p /home/ctf-user/.ssh && echo "{authorized_keys}" > ' f"/home/ctf-user/.ssh/authorized_keys && chmod 600 " f"/home/ctf-user/.ssh/authorized_keys && " f"chown -R ctf-user:ctf-user /home/ctf-user/.ssh",
                ]
            )

            logger.info(f"SSH access configured successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to configure SSH access: {e}")
            return False

    def kill_ssh_session(self, container: GameContainer, clean_ssh_access: bool) -> bool:
        """Kill an SSH session"""
        try:
            logger.info(f"Killing SSH session for container {container.docker_id}")
            self.docker.execute_command(container, ["killall", "-9", "sshd"])

            if clean_ssh_access:
                self.clean_ssh_access(container)

            logger.info(f"SSH access for container {container.docker_id} has been killed and cleaned")
            return True
        except Exception as e:
            logger.error(f"Failed to kill SSH session for container {container}: {e}")
            return False

    def get_ssh_connection_string(self, container: GameContainer) -> Optional[str]:
        """Get SSH connection string for a container"""
        try:
            docker_container = self.docker.get_container(container.docker_id)
            if not docker_container:
                return "Container not available"

            if docker_container.status != "running":
                return "Container not running"

            port = self.docker.get_container_port(docker_container, DockerConstants.SSH_PORT)
            if not port:
                return "Container port not available"

            return f"ssh -p {port} ctf-user@localhost"
        except Exception as e:
            logger.error(f"Failed to get SSH connection string for container {container.docker_id}: {e}")
            return "Error getting connection information"

    def sync_container_status(self, container) -> bool:
        """Sync container status with Docker"""
        try:
            docker_container = self.docker.get_container(container.docker_id)
            if not docker_container:
                container.status = ContainerStatus.ERROR
                container.save(update_fields=['status'])
                return False

            status_map = {
                "created": ContainerStatus.CREATED,
                "running": ContainerStatus.RUNNING,
                "exited": ContainerStatus.STOPPED,
            }

            new_status = status_map.get(docker_container.status, ContainerStatus.ERROR)
            if new_status != container.status:
                container.status = new_status
                container.save(update_fields=['status'])
            return True
        except Exception as e:
            logger.error(f"Failed to sync container status: {e}")
            return False

    def clean_docker_containers(self) -> int:
        """Clean up orphaned Docker containers"""
        logger.info("Cleaning up docker containers...")
        cleaned_count = 0
        game_container_names = set(GameContainer.objects.values_list("name", flat=True))

        try:
            containers = self.docker.list_all_containers()
            for container in containers:
                if container.name.startswith(
                        DockerConstants.CONTAINER_PREFIX) and container.name not in game_container_names:
                    if self.docker.remove_container(container.id, force=True):
                        cleaned_count += 1
                        logger.info(f"Removed orphaned container: {container.id}")
        except Exception as e:
            raise ContainerOperationError(f"Failed to clean containers: {e}")

        return cleaned_count

    def start_container(self, container: GameContainer) -> bool:
        """Start a game container"""
        try:
            if self.docker.start_container(container.docker_id):
                self.sync_container_status(container)
                container.update_activity()

                if container.port:
                    docker_container = self.docker.get_container(container.docker_id)
                    port = self.docker.get_container_port(docker_container, DockerConstants.SSH_PORT)
                    if port and int(port) != container.port:
                        logger.warning(f"Container port changed from {container.port} to {port} - updating record")
                        container.port = int(port)
                        container.save(update_fields=['port'])

                return True
            return False
        except Exception as e:
            logger.error(f"Failed to start container {container.docker_id}: {e}")
            return False

    def stop_session_containers(self, session: GameSession) -> bool:
        """Stop all session containers"""
        try:
            containers = session.get_containers()
            logger.info(f"Stopping {len(containers)} containers for session {session.name}")

            for container in containers:
                self.sync_container_status(container)

                if container.is_running():
                    logger.info(f"Stopping container {container.name}")
                    stopped = self.stop_container(container)
                    if not stopped:
                        logger.warning(f"Failed to stop container {container.name}")
                else:
                    logger.info(f"Container {container.name} is already stopped (status: {container.status})")

            return True
        except Exception as e:
            logger.error(f"Failed to stop session containers: {e}")
            return False

    def stop_container(self, container: GameContainer) -> bool:
        """Stop a game container"""
        try:
            if self.docker.stop_container(container.docker_id):
                self.sync_container_status(container)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to stop container {container.docker_id}: {e}")
            return False
