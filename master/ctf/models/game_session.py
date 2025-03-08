from django.db import models
from django.utils import timezone

from .enums import GameSessionStatus, TeamRole


class GameSession(models.Model):
    name = models.CharField(max_length=128, null=True, unique=True, help_text="Descriptive name for this game session")
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    rotation_period = models.IntegerField(help_text="Period in days")
    status = models.CharField(max_length=16, choices=GameSessionStatus)
    
    class Meta:
        ordering = ["-start_date"]
        
    def __str__(self):
        return f"{self.name} ({self.status})"
    
    def is_active(self):
        """Check if session is currently active"""
        return self.status == GameSessionStatus.ACTIVE and self.start_date <= timezone.now() <= self.end_date
    
    def get_containers(self):
        """Get all containers associated with this session via team assignments"""
        from .container import GameContainer
        container_ids = self.teamassignment_set.values_list('container_id', flat=True).distinct()
        return GameContainer.objects.filter(id__in=container_ids)
    
    def get_teams(self):
        """Get all teams participating in this session"""
        from .team import Team
        team_ids = self.teamassignment_set.values_list('team_id', flat=True).distinct()
        return Team.objects.filter(id__in=team_ids)
    
    def get_active_assignments(self):
        """Get currently active team assignments"""
        now = timezone.now()
        return self.teamassignment_set.filter(start_date__lte=now, end_date__gte=now)


class TeamAssignment(models.Model):
    session = models.ForeignKey(GameSession, on_delete=models.CASCADE)
    team = models.ForeignKey("Team", on_delete=models.CASCADE)
    container = models.ForeignKey("GameContainer", on_delete=models.CASCADE)
    role = models.CharField(max_length=8, choices=TeamRole)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    class Meta:
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["session", "team"]),
            models.Index(fields=["session", "container"]),
        ]
        
    def __str__(self):
        return f"{self.team.name} as {self.role} on {self.container.name}"
    
    def is_active(self):
        """Check if this assignment is currently active"""
        now = timezone.now()
        return self.start_date <= now <= self.end_date
