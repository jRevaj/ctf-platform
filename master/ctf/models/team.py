from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=128)
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

    def update_score(self):
        """Update team's score"""
        self.score = self.blue_points + self.red_points
        self.save()
