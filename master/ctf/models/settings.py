from django.core.exceptions import ValidationError
from django.db import models

from ctf.utils.helpers import validate_cron_expression


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
    process_sessions_cron = models.CharField(
        max_length=100,
        default="0 0 * * *",  # Daily at midnight
        help_text="Cron expression for when to process game sessions (min hour day month weekday)"
    )
    process_phases_cron = models.CharField(
        max_length=100,
        default="0 1 * * *",  # Daily at 1:00 AM
        help_text="Cron expression for when to process phase transitions (min hour day month weekday)"
    )
    check_inactive_deployments_cron = models.CharField(
        max_length=100,
        default="*/15 * * * *",  # Every 15 minutes
        help_text="Cron expression for when to check inactive deployments (min hour day month weekday)"
    )
    monitor_ssh_connections_cron = models.CharField(
        max_length=100,
        default="*/2 * * * *",  # Every 2 minutes
        help_text="Cron expression for when to monitor SSH connections (min hour day month weekday)"
    )
    previous_targets_check_count = models.PositiveIntegerField(
        default=1,
        help_text="Number of previous sessions to check when preventing teams from attacking recent targets"
    )

    def __str__(self):
        return "Global Settings"

    def clean(self):
        if self.max_team_size < 1:
            raise ValidationError("Maximum team size must be at least 1")
        if self.number_of_tiers < 1:
            raise ValidationError("Number of tiers must be at least 1")
        if self.inactive_container_timeout < 1:
            raise ValidationError("Container inactivity timeout must be at least 1 minute")

        validate_cron_expression(self.process_sessions_cron, "Process sessions cron")
        validate_cron_expression(self.process_phases_cron, "Process phases cron")
        validate_cron_expression(self.check_inactive_deployments_cron, "Check inactive deployments cron")
        validate_cron_expression(self.monitor_ssh_connections_cron, "Monitor SSH connections cron")

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
