import logging
import random
import socket
from pathlib import Path

from django.db import models
from django.utils import timezone

from accounts.models.enums import TeamRole
from challenges.models.constants import DockerConstants
from challenges.models.enums import ContainerStatus
from challenges.models.exceptions import ContainerOperationError

logger = logging.getLogger(__name__)


class ChallengeContainerManager(models.Manager):
    """Custom manager for ChallengeContainer model"""

    def create_with_docker(self, template, temp_dir, session, blue_team, docker_service, path="", is_entrypoint=False):
        """Create a new challenge container with Docker container"""
        try:
            template_name = Path(temp_dir).name if temp_dir else template.name
            if path:
                template_container_path = Path(path)
                build_path = str(template_container_path.parent)
                container_name = template_container_path.parent.name
            else:
                build_path = str(template.get_full_template_path())
                container_name = template_name

            tag = f"{DockerConstants.CONTAINER_PREFIX}-{template_name}-{Path(build_path).name}-{session.pk}-{blue_team.pk}"

            docker_service.build_image(build_path, tag)
            port = self.generate_port_number(tag)
            docker_container = docker_service.create_container(container_name=tag, image_tag=tag, port=port)

            return self.create(
                name=tag,
                template_name=container_name,
                docker_id=docker_container.id,
                status=ContainerStatus.RUNNING,
                blue_team=blue_team,
                is_entrypoint=is_entrypoint,
                port=port
            )
        except Exception as e:
            logger.error(f"Failed to create challenge container: {e}")
            raise ContainerOperationError(f"Failed to create container: {e}")

    def get_by_docker_id(self, docker_id):
        """Get container by Docker ID"""
        return self.get(docker_id=docker_id)

    def get_by_ip_address(self, ip_address):
        """Get container by IP address"""
        return self.get(ip_address=ip_address)

    def get_active(self):
        """Get all active containers"""
        return self.filter(status='RUNNING')

    def get_for_team(self, team):
        """Get all containers accessible by a team"""
        return self.filter(
            models.Q(blue_team=team) |
            models.Q(red_team=team)
        )

    def generate_port_number(self, tag):
        """Generate a random port number for new container"""
        max_attempts = 15
        restricted_ranges = [
            (0, 1024),
            (49152, 65535)
        ]

        for attempt in range(max_attempts):
            port = random.randint(30000, 49000)

            in_restricted_range = any(lower <= port <= upper for lower, upper in restricted_ranges)
            if in_restricted_range:
                logger.debug(f"Port {port} is in a restricted range, skipping")
                continue

            if ChallengeContainer.objects.filter(port=port).exists():
                logger.warning(f"Port {port} is already in use in database, attempt {attempt + 1}/{max_attempts}")
                continue

            if self._is_port_available(port):
                logger.info(f"Generated available port {port} for new container {tag}")
                return port
            else:
                logger.warning(f"Port {port} is not available on system, attempt {attempt + 1}/{max_attempts}")

        raise ContainerOperationError(f"Failed to find available port after {max_attempts} attempts")

    @staticmethod
    def _is_port_available(port):
        """Check if a port is available to bind"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return True
            except (socket.error, OSError):
                return False


class ChallengeContainer(models.Model):
    name = models.CharField(max_length=128, unique=True)
    template_name = models.CharField(max_length=128, default="", blank=True)
    docker_id = models.CharField(max_length=128, unique=True)
    status = models.CharField(max_length=16, choices=ContainerStatus, default=ContainerStatus.CREATED)
    port = models.IntegerField(null=True, blank=True)
    services = models.JSONField(default=list)
    deployment = models.ForeignKey('challenges.ChallengeDeployment', null=True, blank=True, related_name="containers",
                                   on_delete=models.CASCADE)
    blue_team = models.ForeignKey(
        'accounts.Team',
        related_name="blue_containers",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    red_team = models.ForeignKey(
        'accounts.Team',
        related_name="red_containers",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    is_entrypoint = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(default=timezone.now)

    objects = ChallengeContainerManager()

    class Meta:
        indexes = [
            models.Index(fields=["docker_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["last_activity"]),
        ]
        verbose_name = "Container"
        verbose_name_plural = "Containers"

    def update_activity(self):
        """Update the last activity timestamp"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])

        if self.deployment:
            self.deployment.update_activity()

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"

    def get_flags(self):
        """Get all flags in the container"""
        return self.flags.all()

    def get_access_history(self):
        """Get access history for the container"""
        if self.deployment:
            from challenges.models.challenge import DeploymentAccess
            return DeploymentAccess.objects.filter(
                deployment=self.deployment,
                containers__contains=[self.id]
            )
        return []

    def get_current_role(self, team):
        """Get team's role in the container"""
        if self.blue_team == team:
            return TeamRole.BLUE
        elif self.red_team == team:
            return TeamRole.RED
        return None

    def is_accessible_by(self, team):
        """Check if team has access to the container"""
        return self.blue_team == team or self.red_team == team

    def is_running(self):
        """Check if container is running"""
        return self.status == ContainerStatus.RUNNING

    def is_stopped(self):
        """Check if container is stopped"""
        return self.status == ContainerStatus.STOPPED

    def get_connection_string(self):
        """Get container connection string"""
        return f"ssh -p {self.port} ctf-user@localhost"

    def delete(self, *args, **kwargs):
        """Override delete method to ensure proper cleanup"""
        from challenges.services import DockerService

        try:
            docker_service = DockerService()
            docker_service.remove_container(self.docker_id, force=True)

            super().delete(*args, **kwargs)

            logger.info(f"Container {self.pk} successfully deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete container {self.pk}: {e}")
            return False
