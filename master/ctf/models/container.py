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

    def create_with_docker(self, template, session, blue_team, docker_service, path=""):
        """Create a new game container with Docker container"""
        try:
            template_name = Path(template.folder).name if template.folder else template.name
            if path:
                template_container_path = Path(path)
                build_path = str(template_container_path.parent)
            else:
                build_path = template.folder if template.folder else str(template.get_full_template_path())
            
            tag = f"{DockerConstants.CONTAINER_PREFIX}-{template_name}-{Path(build_path).name}-{session.pk}-{blue_team.pk}"

            docker_service.build_image(build_path, tag)
            docker_container = docker_service.create_container(container_name=tag, image_tag=tag)

            return self.create(
                name=tag,
                template_name=path if path else template_name,
                docker_id=docker_container.id,
                status=ContainerStatus.RUNNING,
                current_blue_team=blue_team,
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
            models.Q(current_blue_team=team) |
            models.Q(current_red_team=team)
        )


class GameContainer(models.Model):
    name = models.CharField(max_length=128, unique=True)
    template_name = models.CharField(max_length=128, null=True, blank=True)
    docker_id = models.CharField(max_length=128, unique=True)
    status = models.CharField(max_length=16, choices=ContainerStatus)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    services = models.JSONField(default=list)
    current_blue_team = models.ForeignKey(
        Team,
        related_name="blue_containers",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    current_red_team = models.ForeignKey(
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
        if self.current_blue_team == team:
            return TeamRole.BLUE
        elif self.current_red_team == team:
            return TeamRole.RED
        return None

    def is_accessible_by(self, team: Team) -> bool:
        """Check if team has access to the container"""
        return self.current_blue_team == team or self.current_red_team == team


class ContainerAccessHistory(models.Model):
    container = models.ForeignKey(GameContainer, related_name="access_history", on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    role = models.CharField(max_length=8, choices=TeamRole)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
