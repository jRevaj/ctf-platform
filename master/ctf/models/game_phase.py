from django.db import models

from ctf.models.enums import GameSessionStatus, PhaseNumber


class GamePhase(models.Model):
    session = models.ForeignKey("ctf.GameSession", on_delete=models.CASCADE, related_name='phases')
    template = models.ForeignKey("ctf.ChallengeTemplate", on_delete=models.PROTECT, related_name='phases')
    status = models.CharField(max_length=16, choices=GameSessionStatus, default=GameSessionStatus.PLANNED)
    phase_number = models.CharField(max_length=8, choices=PhaseNumber, default=PhaseNumber.FIRST)
    start_date = models.DateTimeField(help_text="Start date of this game phase")

    class Meta:
        ordering = ['phase_number']
        unique_together = ['session', 'phase_number']
        verbose_name = "Game Phase"
        verbose_name_plural = "Game Phases"

    def __str__(self):
        return f"Phase {self.get_phase_number_display()} of {self.session.name}"

    def is_first_phase(self):
        return self.phase_number == PhaseNumber.FIRST

    def is_second_phase(self):
        return self.phase_number == PhaseNumber.SECOND

    def get_team_role(self):
        """Get the primary team role for this phase (blue or red)"""
        return "blue" if self.is_first_phase() else "red"
