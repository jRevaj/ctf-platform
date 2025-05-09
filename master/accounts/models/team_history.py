from django.db import models
from django.utils import timezone


class TeamScoreHistory(models.Model):
    team = models.ForeignKey(
        'accounts.Team',
        related_name='score_history',
        on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField(default=timezone.now)
    score = models.IntegerField(default=0)
    blue_points = models.IntegerField(default=0)
    red_points = models.IntegerField(default=0)

    class Meta:
        ordering = ['team', 'timestamp']
        indexes = [
            models.Index(fields=['team', 'timestamp']),
        ]
        verbose_name = "Team Score History"
        verbose_name_plural = "Team Score History"

    def __str__(self):
        return f"{self.team.name} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {self.score}"

    @classmethod
    def record_score(cls, team):
        """Create a new history record for the current team score."""
        cls.objects.create(
            team=team,
            score=team.score,
            blue_points=team.blue_points,
            red_points=team.red_points
        )
