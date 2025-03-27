from django.db import models

from ctf.models.enums import GameSessionStatus, TeamRole


class GamePhase(models.Model):
    session = models.ForeignKey("ctf.GameSession", on_delete=models.CASCADE, related_name='phases')
    status = models.CharField(max_length=16, choices=GameSessionStatus, default=GameSessionStatus.PLANNED)
    phase_name = models.CharField(max_length=8, choices=TeamRole, default=TeamRole.BLUE)
    start_date = models.DateTimeField(help_text="Start date of this game phase")
    end_date = models.DateTimeField(help_text="End date of this game phase")

    class Meta:
        ordering = ['-start_date']
        unique_together = ['session', 'phase_name']
        verbose_name = "Game Phase"
        verbose_name_plural = "Game Phases"

    def __str__(self):
        return f"Phase {self.phase_name} of {self.session.name}"

    def is_blue_phase(self):
        return self.phase_name == TeamRole.BLUE

    def is_red_phase(self):
        return self.phase_name == TeamRole.RED

    def get_team_role(self):
        """Get the primary team role for this phase (blue or red)"""
        return "blue" if self.is_blue_phase() else "red"
