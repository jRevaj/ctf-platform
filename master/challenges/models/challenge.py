import logging
import os
import shutil
import uuid
from datetime import timedelta
from pathlib import Path
from zipfile import ZipFile

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from challenges.utils.helpers import get_time_string_from_seconds
from challenges.utils.template_helpers import read_template_info

logger = logging.getLogger(__name__)


class ChallengeTemplate(models.Model):
    folder = models.CharField(max_length=128, unique=True, null=True,
                              help_text="Folder name in game-templates directory")
    name = models.CharField(max_length=64, null=True, blank=True)
    title = models.CharField(max_length=256, default="", blank=True)
    description = models.TextField(default="", blank=True)
    docker_compose = models.TextField(default="", blank=True)
    containers_config = models.JSONField(default=dict, null=True, blank=True)
    networks_config = models.JSONField(default=dict, null=True, blank=True)
    template_file = models.FileField(upload_to='ctf/static/uploads/', null=True, blank=True,
                                     help_text="Upload a zip file containing the scenario folder")

    class Meta:
        verbose_name = "Template"
        verbose_name_plural = "Templates"

    def __str__(self) -> str:
        return self.name or self.folder or "Unnamed Template"

    def get_template_folder(self) -> str:
        return f"game-challenges/{self.name or self.folder}"

    def get_full_template_path(self) -> Path:
        return Path(settings.BASE_DIR) / self.get_template_folder()

    def clean(self):
        if self.template_file and not self.template_file.name.endswith('.zip'):
            raise ValidationError({'template_file': 'Only zip files are allowed.'})

        if not self.template_file and (not self.name or not self.title):
            if not self.name:
                raise ValidationError({'name': 'Name is required when not uploading a template file'})
            if not self.title:
                raise ValidationError({'title': 'Title is required when not uploading a template file'})

    def save(self, *args, **kwargs):
        template_file = self.template_file
        if template_file:
            try:
                super().save(*args, **kwargs)

                with ZipFile(template_file.path, 'r') as zip_ref:
                    first_dir = next((name for name in zip_ref.namelist() if name.endswith('/')), None)
                    if not first_dir:
                        raise ValidationError('Zip file must contain a directory.')

                    self.folder = first_dir.rstrip('/')
                    self.name = self.folder

                    target_dir = self.get_full_template_path()
                    target_dir.mkdir(parents=True, exist_ok=True)

                    zip_ref.extractall(target_dir.parent)

                    template_info = read_template_info(target_dir)
                    if template_info:
                        self.title = template_info.get('title', '')
                        self.description = template_info.get('description', '')
                        self.docker_compose = template_info.get('docker_compose', '')
                        self.containers_config = template_info.get('containers', {})
                        self.networks_config = template_info.get('networks', {})
                    else:
                        raise ValidationError('Failed to read template information')

                if os.path.exists(template_file.path):
                    os.remove(template_file.path)
                self.template_file = None

                super().save(update_fields=['folder', 'name', 'title', 'description', 'docker_compose',
                                            'containers_config', 'networks_config', 'template_file'])
            except Exception as e:
                if os.path.exists(template_file.path):
                    os.remove(template_file.path)
                raise ValidationError(f'Error processing zip file: {str(e)}')
        else:
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Delete the template folder when the template is deleted"""
        template_path = self.get_full_template_path()
        if template_path.exists():
            try:
                shutil.rmtree(template_path)
                logger.info(f"Deleted template folder: {template_path}")
            except Exception as e:
                logger.error(f"Failed to delete template folder {template_path}: {e}")
        super().delete(*args, **kwargs)


class ChallengeNetworkConfig(models.Model):
    name = models.CharField(max_length=128, default="")
    subnet = models.GenericIPAddressField()
    docker_id = models.CharField(max_length=128, unique=True)
    template = models.ForeignKey('challenges.ChallengeTemplate', on_delete=models.PROTECT)
    deployment = models.ForeignKey('challenges.ChallengeDeployment', related_name="networks", on_delete=models.CASCADE)
    containers = models.ManyToManyField('challenges.ChallengeContainer', related_name="challenge_network_configs")

    class Meta:
        verbose_name = "Network Config"
        verbose_name_plural = "Network Configs"

    def __str__(self):
        return f"Network {self.name or 'Default'} ({self.subnet})"

    def delete(self, *args, **kwargs):
        """Delete the Docker network when the model is deleted."""
        try:
            from challenges.services import DockerService
            docker_service = DockerService()
            docker_network = docker_service.get_network(self.docker_id)
            docker_service.remove_network(docker_network)
            super().delete(*args, **kwargs)
            logger.info(f"Network {self.pk} successfully deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete network {self.pk}: {e}")
            return False


class ChallengeDeployment(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    template = models.ForeignKey('challenges.ChallengeTemplate', related_name="deployments", on_delete=models.PROTECT)
    last_activity = models.DateTimeField(default=timezone.now)
    has_active_connections = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Deployment"
        verbose_name_plural = "Deployments"

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
        return get_time_string_from_seconds(
            sum(access.total_duration.total_seconds() for access in self.access_records.filter(team=self.blue_team)))

    @property
    def total_red_access_time(self):
        return get_time_string_from_seconds(
            sum(access.total_duration.total_seconds() for access in self.access_records.filter(team=self.red_team)))

    def update_activity(self):
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])

    def start_containers(self) -> bool:
        """Start all containers in this deployment"""
        from challenges.services import DeploymentService
        return DeploymentService().start_deployment(self)

    def stop_containers(self) -> bool:
        """Stop all containers in this deployment"""
        from challenges.services import DeploymentService
        return DeploymentService().stop_deployment(self)

    def sync_container_status(self) -> bool:
        """Sync status of all containers in this deployment"""
        from challenges.services import DeploymentService
        return DeploymentService().sync_deployment_status(self)

    def is_running(self) -> bool:
        """Check if any container in this deployment is running"""
        containers = self.containers.all()
        if not containers:
            return False
        return any(container.is_running() for container in containers)


class DeploymentAccess(models.Model):
    deployment = models.ForeignKey(ChallengeDeployment, related_name="access_records", on_delete=models.CASCADE)
    team = models.ForeignKey("accounts.Team", on_delete=models.CASCADE)
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
