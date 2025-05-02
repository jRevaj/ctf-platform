import logging
import uuid
from pathlib import Path
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class ChallengeTemplate(models.Model):
    folder = models.CharField(max_length=128, unique=True, null=True,
                              help_text="Folder name in game-templates directory")
    name = models.CharField(max_length=64)
    title = models.CharField(max_length=256, default="")
    description = models.TextField(default="", blank=True)
    docker_compose = models.TextField(default="", blank=True)
    containers_config = models.JSONField(default=dict, null=True, blank=True)
    networks_config = models.JSONField(default=dict, null=True, blank=True)

    class Meta:
        verbose_name = "Challenge Template"
        verbose_name_plural = "Challenge Templates"

    def __str__(self) -> str:
        return self.name

    def get_template_folder(self) -> str:
        return f"game-challenges/{self.name}"

    def get_full_template_path(self) -> Path:
        return Path(settings.BASE_DIR) / self.get_template_folder()


class ChallengeNetworkConfig(models.Model):
    name = models.CharField(max_length=128, default="")
    subnet = models.GenericIPAddressField()
    template = models.ForeignKey('ctf.ChallengeTemplate', on_delete=models.PROTECT)
    deployment = models.ForeignKey('ctf.ChallengeDeployment', related_name="networks", on_delete=models.CASCADE)
    containers = models.ManyToManyField('ctf.GameContainer', related_name="challenge_network_configs")

    class Meta:
        verbose_name = "Challenge Network Config"
        verbose_name_plural = "Challenge Network Configs"

    def __str__(self):
        return f"Network {self.name or 'Default'} ({self.subnet})"


class ChallengeDeployment(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    template = models.ForeignKey('ctf.ChallengeTemplate', related_name="deployments", on_delete=models.PROTECT)
    last_activity = models.DateTimeField(default=timezone.now)
    has_active_connections = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Challenge Deployment"
        verbose_name_plural = "Challenge Deployments"

    def __str__(self):
        return f"Deployment {self.template.name} ({self.template.pk})"

    @property
    def blue_team(self):
        return self.containers.first().blue_team

    @property
    def red_team(self):
        return self.containers.first().red_team

    @property
    def total_blue_access_time(self):
        return sum(access.total_duration.total_seconds() for access in self.access_records.filter(team=self.blue_team))

    @property
    def total_red_access_time(self):
        return sum(access.total_duration.total_seconds() for access in self.access_records.filter(team=self.red_team))

    def update_activity(self):
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])

    def start_containers(self) -> bool:
        """Start all containers in this deployment"""
        from ctf.services import DeploymentService
        return DeploymentService().start_deployment(self)

    def stop_containers(self) -> bool:
        """Stop all containers in this deployment"""
        from ctf.services import DeploymentService
        return DeploymentService().stop_deployment(self)

    def sync_container_status(self) -> bool:
        """Sync status of all containers in this deployment"""
        from ctf.services import DeploymentService
        return DeploymentService().sync_deployment_status(self)

    def is_running(self) -> bool:
        """Check if any container in this deployment is running"""
        containers = self.containers.all()
        if not containers:
            return False
        return any(container.is_running() for container in containers)


class DeploymentAccess(models.Model):
    deployment = models.ForeignKey(ChallengeDeployment, related_name="access_records", on_delete=models.CASCADE)
    team = models.ForeignKey("ctf.Team", on_delete=models.CASCADE)
    session_id = models.CharField(max_length=256, null=True, blank=True)
    access_type = models.CharField(max_length=50)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    containers = models.JSONField(default=list, help_text="List of container IDs accessed during this session")

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['deployment', 'is_active']),
        ]
        verbose_name = "Deployment Access"
        verbose_name_plural = "Deployment Accesses"

    def save(self, *args, **kwargs):
        """Override save to update deployment activity"""
        super().save(*args, **kwargs)
        self.deployment.update_activity()

    def end_session(self):
        """End the current session"""
        self.end_time = timezone.now()
        self.is_active = False
        self.duration = self.end_time - self.start_time
        self.save(update_fields=['end_time', 'is_active', 'duration'])

    def get_current_duration(self):
        """Get the current duration of an active session"""
        if not self.is_active:
            return self.duration or timedelta(0)
        return timezone.now() - self.start_time

    @property
    def total_duration(self):
        """Get total duration including active session time"""
        if self.is_active:
            return self.get_current_duration()
        return self.duration or timedelta(0)
