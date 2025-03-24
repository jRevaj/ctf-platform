from django.db import models
from django.utils import timezone

from ctf.models.container import GameContainer
from ctf.models.enums import GameSessionStatus, TeamRole
from ctf.models.team import Team


class GameSession(models.Model):
    name = models.CharField(max_length=128, unique=True, help_text="Descriptive name for this game session")
    template = models.ForeignKey("ctf.ChallengeTemplate", null=True, on_delete=models.PROTECT, related_name="game_sessions")
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    rotation_period = models.IntegerField(help_text="Period in days")
    status = models.CharField(max_length=16, choices=GameSessionStatus, default=GameSessionStatus.PLANNED)

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Game Session"
        verbose_name_plural = "Game Sessions"

    def __str__(self):
        return f"{self.name} ({self.status})"

    def is_active(self):
        """Check if session is currently active"""
        return self.status == GameSessionStatus.ACTIVE and self.start_date <= timezone.now() <= self.end_date

    def get_containers(self):
        """Get all containers associated with this session via team assignments"""
        container_ids = self.team_assignments.values_list('container_id', flat=True).distinct()
        return GameContainer.objects.filter(id__in=container_ids)

    def get_teams(self):
        """Get all teams participating in this session"""
        team_ids = self.team_assignments.values_list('team_id', flat=True).distinct()
        return Team.objects.filter(id__in=team_ids)

    def get_active_assignments(self):
        """Get currently active team assignments"""
        now = timezone.now()
        return self.team_assignments.filter(start_date__lte=now, end_date__gte=now)


class TeamAssignment(models.Model):
    session = models.ForeignKey(GameSession, on_delete=models.CASCADE, related_name="team_assignments")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="team_assignments")
    container = models.ForeignKey("ctf.GameContainer", on_delete=models.CASCADE, related_name="team_assignments")
    role = models.CharField(max_length=8, choices=TeamRole, default=TeamRole.BLUE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    class Meta:
        ordering = ["-start_date"]
        indexes = [models.Index(fields=["session", "team"]), models.Index(fields=["session", "container"])]
        verbose_name = "Team Assignment"
        verbose_name_plural = "Team Assignments"

    def __str__(self):
        return f"{self.team.name} as {self.role} on {self.container.name}"

    def is_active(self):
        """Check if this assignment is currently active"""
        now = timezone.now()
        return self.start_date <= now <= self.end_date
