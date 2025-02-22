from pathlib import Path

from django.conf import settings
from django.db import models

from ctf.models.container import GameContainer


class ScenarioTemplate(models.Model):
    folder = models.CharField(
        max_length=128,
        unique=True,
        null=True,
        help_text="Folder name in game-scenarios directory",
    )
    name = models.CharField(max_length=64)
    title = models.CharField(max_length=256, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    docker_compose = models.TextField(null=True, blank=True)
    containers_config = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return self.name

    def get_folder(self) -> str:
        return f"game-scenarios/{self.folder}"

    def get_full_path(self) -> Path:
        return Path(settings.BASE_DIR) / self.get_folder()
    

class ScenarioNetworkConfig(models.Model):
    template = models.ForeignKey(ScenarioTemplate, on_delete=models.PROTECT)
    subnet = models.GenericIPAddressField()
    used_ips = models.JSONField(default=list)
    containers = models.ManyToManyField(GameContainer, related_name="scenario_network_config")


class ScenarioArchitecture(models.Model):
    template = models.ForeignKey(ScenarioTemplate, on_delete=models.PROTECT)
    containers = models.ManyToManyField(GameContainer, related_name="scenario_architecture")
    network = models.ForeignKey(ScenarioNetworkConfig, on_delete=models.PROTECT)

    # objects = ScenarioArchitectureManager()
