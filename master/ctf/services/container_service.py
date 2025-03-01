import logging
from typing import Optional

from ctf.models import GameContainer, ContainerStatus, Team
from ctf.models.constants import DockerConstants
from ctf.models.exceptions import ContainerOperationError
from .docker_service import DockerService

logger = logging.getLogger(__name__)


class ContainerService:
    """Business logic for container operations"""

    def __init__(self, docker_service: DockerService):
        self.docker = docker_service

    def create_related_containers(self, template, session, blue_team):
        """Batch create related containers"""
        try:
            dockerfiles = []
            containers = []
            for filepath in template.get_full_template_path().rglob("*"):
                if filepath.is_file():
                    if filepath.name == 'Dockerfile' or filepath.name.startswith('Dockerfile.'):
                        dockerfiles.append(filepath)

            for dockerfile in dockerfiles:
                container = self.create_game_container(template, session, blue_team, dockerfile)
                containers.append(container)

            logger.info(f"Created {len(containers)} related containers: {containers}")
            return containers
        except ContainerOperationError as e:
            logger.error(f"Error batch creating containers: {e}")
            return []
        except Exception as e:
            logger.error(f"Error batch creating containers: {e}")
            return []

    def create_game_container(self, template, session, blue_team, path="") -> Optional[GameContainer]:
        """Create a new game container from template"""
        try:
            logger.info(f"Creating new game container {path if path else template.folder}")
            return GameContainer.objects.create_with_docker(template=template, session=session, blue_team=blue_team,
                                                            docker_service=self.docker, path=path)
        except Exception as e:
            logger.error(f"Failed to create game container: {e}")
            return None

    def delete_game_container(self, container: GameContainer) -> bool:
        """Delete a game container and its Docker container"""
        container_pk = container.pk
        try:
            self.docker.remove_container(container.docker_id, force=True)
            container.delete()
            logger.info(f"Container {container_pk} successfully deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete container {container_pk}: {e}")
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

    def get_ssh_connection_string(self, container: GameContainer) -> Optional[str]:
        """Get SSH connection string for a container"""
        try:
            docker_container = self.docker.get_container(container.docker_id)
            if not docker_container:
                return None

            port = self.docker.get_container_port(docker_container, "22/tcp")
            if not port:
                return None

            return f"ssh -p {port} ctf-user@localhost"
        except Exception as e:
            logger.error(f"Failed to get SSH connection string: {e}")
            return None

    def sync_container_status(self, container) -> bool:
        """Sync container status with Docker"""
        try:
            docker_container = self.docker.get_container(container.docker_id)
            if not docker_container:
                container.status = ContainerStatus.ERROR
                container.save()
                return False

            status_map = {
                "created": ContainerStatus.CREATED,
                "running": ContainerStatus.RUNNING,
                "exited": ContainerStatus.STOPPED,
            }

            new_status = status_map.get(docker_container.status, ContainerStatus.ERROR)
            if new_status != container.status:
                container.status = new_status
                container.save()
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
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to start container {container.docker_id}: {e}")
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
