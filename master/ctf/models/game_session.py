from datetime import timedelta

from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from ctf.models import GamePhase
from ctf.models.enums import GameSessionStatus, TeamRole

class GameSession(models.Model):
    name = models.CharField(max_length=128, unique=True, help_text="Descriptive name for this game session")
    template = models.ForeignKey("ctf.ChallengeTemplate", null=True, on_delete=models.PROTECT,
                                 related_name="game_sessions")
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True)
    rotation_period = models.IntegerField(help_text="Period in days")
    status = models.CharField(max_length=16, choices=GameSessionStatus, default=GameSessionStatus.PLANNED)

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Game Session"
        verbose_name_plural = "Game Sessions"

    def __str__(self):
        return f"{self.name} ({self.status})"

    def is_active(self):
        """Check if session is currently active"""
        return self.status == GameSessionStatus.ACTIVE and self.start_date <= timezone.now() <= self.end_date

    def get_containers(self):
        """Get all containers associated with this session via team assignments"""
        from ctf.models.container import GameContainer
        deployment_ids = self.team_assignments.values_list('deployment_id', flat=True).distinct()
        return GameContainer.objects.filter(deployment_id__in=deployment_ids)

    def get_teams(self):
        """Get all teams participating in this session"""
        from ctf.models import Team
        return Team.objects.filter(assignments__session=self).distinct()

    def get_active_assignments(self):
        """Get currently active team assignments"""
        now = timezone.now()
        return self.team_assignments.filter(start_date__lte=now, end_date__gte=now)


@receiver(post_save, sender=GameSession)
def create_related_models(sender, instance, created, **kwargs):
    if created:
        instance.end_date = instance.start_date + timedelta(days=instance.rotation_period * 2)
        instance.save(update_fields=['end_date'])

        GamePhase.objects.create(
            session=instance,
            status=instance.status,
            start_date=instance.start_date,
            end_date=instance.start_date + timedelta(days=instance.rotation_period),
        )
        GamePhase.objects.create(
            session=instance,
            status=GameSessionStatus.PLANNED,
            phase_name=TeamRole.RED,
            start_date=instance.start_date + timedelta(days=instance.rotation_period),
            end_date=instance.end_date,
        )


@receiver(pre_save, sender=GameSession)
def track_status_change(sender, instance, **kwargs):
    """Track if status is changing to COMPLETED"""
    if instance.pk:
        try:
            old_instance = GameSession.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except GameSession.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=GameSession)
def handle_completed_session(sender, instance, created, **kwargs):
    """Handle cleanup when a game session is marked as completed"""
    if instance.status == GameSessionStatus.COMPLETED:
        old_status = getattr(instance, '_old_status', None)
        if old_status != GameSessionStatus.COMPLETED:
            # TODO: distribute the remaining points of flags that was not captured to blue teams
            from ctf.services import ContainerService
            instance.phases.all().update(status=GameSessionStatus.COMPLETED)
            ContainerService().stop_session_containers(instance)


class TeamAssignment(models.Model):
    session = models.ForeignKey(GameSession, on_delete=models.CASCADE, related_name="team_assignments")
    team = models.ForeignKey("ctf.Team", on_delete=models.CASCADE, related_name="assignments")
    deployment = models.ForeignKey("ctf.ChallengeDeployment", on_delete=models.CASCADE, related_name="assignments")
    role = models.CharField(max_length=8, choices=TeamRole, default=TeamRole.BLUE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    class Meta:
        ordering = ["-start_date"]
        indexes = [models.Index(fields=["session", "team"]), models.Index(fields=["session", "deployment"])]
        verbose_name = "Team Assignment"
        verbose_name_plural = "Team Assignments"

    def __str__(self):
        return f"{self.team.name} as {self.role} on {self.deployment.pk}"

    def is_active(self):
        """Check if this assignment is currently active"""
        now = timezone.now()
        return self.start_date <= now <= self.end_date
