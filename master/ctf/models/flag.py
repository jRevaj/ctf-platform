from datetime import datetime, timezone
from django.db import models

from ctf.managers.flag_manager import FlagManager
from .container import GameContainer
from .team import Team


class Flag(models.Model):
    value = models.CharField(max_length=128, unique=True)
    container = models.ForeignKey(
        GameContainer, related_name="flags", on_delete=models.CASCADE
    )
    points = models.IntegerField(default=100)
    owner = models.ForeignKey(
        Team,
        related_name="owned_flags",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    is_captured = models.BooleanField(default=False)
    captured_by = models.ForeignKey(
        Team,
        related_name="captured_flags",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    captured_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = FlagManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["value"]),
        ]

    def __str__(self):
        return self.value

    def capture(self, team: Team):
        """Mark the flag as captured"""
        self.is_captured = True
        self.captured_by = team
        self.captured_at = datetime.now(timezone.utc)
        self.save()

    def release(self):
        """Release the flag"""
        self.is_captured = False
        self.captured_by = None
        self.captured_at = None
        self.save()
