from django.db import models

from .enums import GameSessionStatus, TeamRole


class GameSession(models.Model):
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    rotation_period = models.IntegerField(help_text="Period in days")
    status = models.CharField(max_length=16, choices=GameSessionStatus.choices)


class TeamAssignment(models.Model):
    session = models.ForeignKey(GameSession, on_delete=models.CASCADE)
    team = models.ForeignKey("Team", on_delete=models.CASCADE)
    container = models.ForeignKey("GameContainer", on_delete=models.CASCADE)
    role = models.CharField(max_length=8, choices=TeamRole.choices)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
