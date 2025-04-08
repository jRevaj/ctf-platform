import logging
from pathlib import Path

from django.db import models
from django.utils import timezone

from ctf.models.constants import DockerConstants
from ctf.models.enums import ContainerStatus, TeamRole
from ctf.models.exceptions import ContainerOperationError

logger = logging.getLogger(__name__)


class GameContainerManager(models.Manager):
    """Custom manager for GameContainer model"""

    def create_with_docker(self, template, temp_dir, session, blue_team, docker_service, path="", is_entrypoint=False):
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
                is_entrypoint=is_entrypoint
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
    template_name = models.CharField(max_length=128, default="", blank=True)
    docker_id = models.CharField(max_length=128, unique=True)
    status = models.CharField(max_length=16, choices=ContainerStatus, default=ContainerStatus.CREATED)
    port = models.IntegerField(null=True, blank=True)
    services = models.JSONField(default=list)
    deployment = models.ForeignKey('ctf.ChallengeDeployment', null=True, blank=True, related_name="containers",
                                   on_delete=models.CASCADE)
    blue_team = models.ForeignKey(
        'ctf.Team',
        related_name="blue_containers",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    red_team = models.ForeignKey(
        'ctf.Team',
        related_name="red_containers",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    is_entrypoint = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = GameContainerManager()

    class Meta:
        indexes = [
            models.Index(fields=["docker_id"]),
            models.Index(fields=["status"]),
        ]
        verbose_name = "Game Container"
        verbose_name_plural = "Game Containers"

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"

    def get_flags(self):
        """Get all flags in the container"""
        return self.flags.all()

    def get_access_history(self):
        """Get access history for the container"""
        return self.access_records.all()

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

    def get_connection_string(self):
        """Get container connection string"""
        return f"ssh -p {self.port} ctf-user@localhost"

    def cleanup_docker_container(self):
        """Clean up the associated Docker container"""
        from ctf.services import ContainerService
        from ctf.models.enums import ContainerStatus
        
        container_service = ContainerService()
        try:
            container_service.sync_container_status(self)
            
            if self.status == ContainerStatus.RUNNING:
                if not container_service.stop_container(self):
                    logger.error(f"Failed to stop container {self.docker_id} before deletion")
                container_service.sync_container_status(self)
            
            container_service.delete_game_container(self)
        except Exception as e:
            logger.error(f"Failed to delete Docker container {self.docker_id} during model deletion: {e}")

    def delete(self, *args, **kwargs):
        """Override delete to ensure Docker container is also deleted"""
        self.cleanup_docker_container()
        super().delete(*args, **kwargs)


class ContainerAccess(models.Model):
    container = models.ForeignKey(GameContainer, related_name="access_records", on_delete=models.CASCADE)
    team = models.ForeignKey('ctf.Team', related_name="container_access_history", on_delete=models.CASCADE)
    user = models.ForeignKey('ctf.User', related_name="container_access", on_delete=models.CASCADE, null=True,
                             blank=True)
    role = models.CharField(max_length=8, choices=TeamRole)
    access_type = models.CharField(max_length=64)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    session_length = models.DurationField(null=True, blank=True, help_text="Duration of session if applicable")
    commands_executed = models.TextField(default="", blank=True, help_text="Commands executed during session")

    class Meta:
        ordering = ["-start_time"]
        indexes = [
            models.Index(fields=["container", "start_time"]),
            models.Index(fields=["team", "start_time"]),
            models.Index(fields=["user", "start_time"]),
            models.Index(fields=["access_type"]),
        ]
        verbose_name = "Container Access Record"
        verbose_name_plural = "Container Access Records"

    def __str__(self):
        if self.access_type == 'SESSION':
            return f"{self.team.name} - {self.role} access to {self.container.name} from {self.start_time} to {self.end_time or 'ongoing'}"
        else:
            return f"{self.user} - {self.access_type} - {self.container.name} at {self.start_time}"

    def calculate_session_length(self):
        """Calculate and update the session length if end_time is set"""
        if self.end_time:
            self.session_length = self.end_time - self.start_time
            return self.session_length
        return None

    def end_session(self):
        """End the current session"""
        if not self.end_time:
            self.end_time = timezone.now()
            self.calculate_session_length()
            self.save()
