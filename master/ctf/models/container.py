import logging
from typing import Optional

from django.db import models

from ctf.managers.container_manager import GameContainerManager
from .enums import ContainerStatus, TeamRole
from .team import Team

logger = logging.getLogger(__name__)


class ContainerTemplate(models.Model):
    folder = models.CharField(
        max_length=128,
        unique=True,
        null=True,
        help_text="Folder name in container-templates directory",
    )
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)
    docker_compose = models.TextField()


class GameContainer(models.Model):
    name = models.CharField(max_length=128, unique=True)
    docker_id = models.CharField(max_length=128, unique=True)
    status = models.CharField(max_length=16, choices=ContainerStatus.choices)
    template = models.ForeignKey(ContainerTemplate, on_delete=models.PROTECT)
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
    role = models.CharField(max_length=8, choices=TeamRole.choices)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
