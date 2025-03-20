import logging
from pathlib import Path
from typing import Optional

from django.db import models

from .constants import DockerConstants
from .enums import ContainerStatus, TeamRole
from .exceptions import ContainerOperationError
from .team import Team

logger = logging.getLogger(__name__)


class GameContainerManager(models.Manager):
    """Custom manager for GameContainer model"""

    def create_with_docker(self, template, temp_dir, session, blue_team, docker_service, path=""):
        """Create a new game container with Docker container"""
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
            docker_container = docker_service.create_container(container_name=tag, image_tag=tag)

            return self.create(
                name=tag,
                template_name=container_name,
                docker_id=docker_container.id,
                status=ContainerStatus.RUNNING,
                blue_team=blue_team,
                access_rotation_date=session.end_date,
            )
        except Exception as e:
            logger.error(f"Failed to create game container: {e}")
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


class GameContainer(models.Model):
    name = models.CharField(max_length=128, unique=True)
    template_name = models.CharField(max_length=128, null=True, blank=True)
    docker_id = models.CharField(max_length=128, unique=True)
    status = models.CharField(max_length=16, choices=ContainerStatus)
    port = models.IntegerField(null=True, blank=True)
    services = models.JSONField(default=list)
    blue_team = models.ForeignKey(
        Team,
        related_name="blue_containers",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    red_team = models.ForeignKey(
        Team,
        related_name="red_containers",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    access_rotation_date = models.DateTimeField()

    objects = GameContainerManager()

    class Meta:
        ordering = ["-access_rotation_date"]
        indexes = [
            models.Index(fields=["docker_id"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return self.name

    def get_flags(self):
        """Get all flags in the container"""
        return self.flags.all()

    def get_access_history(self):
        """Get access history for the container"""
        return self.access_history.all()

    def get_current_role(self, team: Team) -> Optional[TeamRole]:
        """Get team's role in the container"""
        if self.blue_team == team:
            return TeamRole.BLUE
        elif self.red_team == team:
            return TeamRole.RED
        return None

    def is_accessible_by(self, team: Team) -> bool:
        """Check if team has access to the container"""
        return self.blue_team == team or self.red_team == team

    def get_connection_string(self):
        """Get container connection string"""
        return f"ssh -p {self.port} ctf-user@localhost"


class ContainerAccessHistory(models.Model):
    container = models.ForeignKey(GameContainer, related_name="access_history", on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    role = models.CharField(max_length=8, choices=TeamRole)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()


class ContainerAccessLog(models.Model):
    """Model to track individual SSH and other access attempts to containers"""
    container = models.ForeignKey(GameContainer, related_name="access_logs", on_delete=models.CASCADE)
    user = models.ForeignKey('User', related_name="container_access", on_delete=models.CASCADE)
    access_type = models.CharField(max_length=16, choices=[
        ('SSH', 'SSH Connection'),
        ('HTTP', 'Web Access'),
        ('API', 'API Access'),
        ('OTHER', 'Other Access')
    ])
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    session_length = models.DurationField(null=True, blank=True, help_text="Duration of session if applicable")
    commands_executed = models.TextField(null=True, blank=True, help_text="Commands executed during session")

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["container", "timestamp"]),
            models.Index(fields=["user", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.access_type} - {self.container.name} at {self.timestamp}"
