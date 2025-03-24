from django.db import models

from .enums import TeamRole


class Team(models.Model):
    name = models.CharField(max_length=128)
    role = models.CharField(max_length=8, choices=TeamRole, default=TeamRole.BLUE)
    score = models.IntegerField(default=0)
    red_points = models.IntegerField(default=0)
    blue_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def flags(self):
        """Get all flags owned by the team using reverse relation"""
        return self.owned_flags.all()

    def update_score(self, points):
        """Update team's score"""
        self.score += points
        self.save()

    def rotate_role(self):
        """Rotate team's role between red and blue"""
        self.role = TeamRole.RED if self.role == TeamRole.BLUE else TeamRole.BLUE
        self.save()
