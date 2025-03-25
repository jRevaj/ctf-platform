import logging
from pathlib import Path

from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


class ChallengeTemplate(models.Model):
    folder = models.CharField(max_length=128, unique=True, null=True,
                              help_text="Folder name in game-templates directory")
    name = models.CharField(max_length=64)
    title = models.CharField(max_length=256, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    docker_compose = models.TextField(null=True, blank=True)
    containers_config = models.JSONField(default=dict, null=True, blank=True)
    networks_config = models.JSONField(default=dict, null=True, blank=True)

    def __str__(self) -> str:
        return self.name

    def get_template_folder(self) -> str:
        return f"game-challenges/{self.name}"

    def get_full_template_path(self) -> Path:
        return Path(settings.BASE_DIR) / self.get_template_folder()


class ChallengeNetworkConfig(models.Model):
    name = models.CharField(max_length=128, null=True, blank=True)
    subnet = models.GenericIPAddressField()
    template = models.ForeignKey('ctf.ChallengeTemplate', on_delete=models.PROTECT)
    deployment = models.ForeignKey('ctf.ChallengeDeployment', related_name="networks", on_delete=models.CASCADE)
    containers = models.ManyToManyField('ctf.GameContainer', related_name="challenge_network_configs")

    def __str__(self):
        return f"Network {self.name or 'Default'} ({self.subnet})"


class ChallengeDeployment(models.Model):
    template = models.ForeignKey('ctf.ChallengeTemplate', related_name="deployments", on_delete=models.PROTECT)

    def __str__(self):
        return f"Deployment {self.template.name} ({self.template.pk})"
