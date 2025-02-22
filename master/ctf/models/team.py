from django.db import models

from .enums import TeamRole


class Team(models.Model):
    name = models.CharField(max_length=128)
    role = models.CharField(max_length=8, choices=TeamRole.choices)
    score = models.IntegerField(default=0)
    red_points = models.IntegerField(default=0)
    blue_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def get_flags(self):
        """Get all flags owned by the team"""
        return self.owned_flags.all()
