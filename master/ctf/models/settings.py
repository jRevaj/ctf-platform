from django.core.exceptions import ValidationError
from django.db import models


class GlobalSettings(models.Model):
    max_team_size = models.PositiveIntegerField(
        default=3,
        help_text="Maximum number of players allowed in a team"
    )
    number_of_tiers = models.PositiveIntegerField(
        default=3,
        help_text="Number of tiers to use in matchmaking"
    )
    allow_team_changes = models.BooleanField(
        default=True,
        help_text="Whether players can change teams outside of games"
    )
    enable_auto_container_shutdown = models.BooleanField(
        default=True,
        help_text="Whether to automatically shut down inactive containers"
    )
    inactive_container_timeout = models.PositiveIntegerField(
        default=30,
        help_text="Number of minutes to wait before stopping an inactive container"
    )
    previous_targets_check_count = models.PositiveIntegerField(
        default=1,
        help_text="Number of previous sessions to check when preventing teams from attacking recent targets"
    )

    class Meta:
        verbose_name = "Global Settings"
        verbose_name_plural = "Global Settings"

    def __str__(self):
        return "Global Settings"

    def clean(self):
        if self.max_team_size < 1:
            raise ValidationError("Maximum team size must be at least 1")
        if self.number_of_tiers < 1:
            raise ValidationError("Number of tiers must be at least 1")
        if self.inactive_container_timeout < 1:
            raise ValidationError("Container inactivity timeout must be at least 1 minute")

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.pk and GlobalSettings.objects.exists():
            raise ValidationError("Only one settings instance can exist")
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Get the current settings, creating default if none exist"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
