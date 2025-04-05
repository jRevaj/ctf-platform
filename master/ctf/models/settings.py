from django.core.exceptions import ValidationError
from django.db import models


class GlobalSettings(models.Model):
    max_team_size = models.PositiveIntegerField(
        default=4,
        help_text="Maximum number of players allowed in a team"
    )
    allow_team_changes = models.BooleanField(
        default=True,
        help_text="Whether players can change teams outside of games"
    )

    def clean(self):
        if self.max_team_size < 1:
            raise ValidationError("Maximum team size must be at least 1")

    def save(self, *args, **kwargs):
        self.full_clean()
        # Ensure only one settings instance exists
        if not self.pk and GlobalSettings.objects.exists():
            raise ValidationError("Only one settings instance can exist")
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Get the current settings, creating default if none exist"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings

    def __str__(self):
        return "Global Settings"
