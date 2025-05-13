import random
import uuid
from datetime import timedelta

from django.db import models
from django.db.models import QuerySet, Q
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from accounts.models.enums import TeamRole
from ctf.models import GamePhase, Flag
from ctf.models.enums import GameSessionStatus, GamePhaseStatus


class GameSession(models.Model):
    name = models.CharField(max_length=128, unique=True, help_text="Descriptive name for this game session")
    template = models.ForeignKey("challenges.ChallengeTemplate", null=True, on_delete=models.PROTECT,
                                 related_name="game_sessions")
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True)
    rotation_period = models.PositiveIntegerField(help_text="Period in days")
    status = models.CharField(max_length=16, choices=GameSessionStatus, default=GameSessionStatus.PLANNED)

    enable_time_restrictions = models.BooleanField(
        default=False,
        help_text="Whether to enable time restrictions for accessing deployments"
    )
    max_blue_team_time = models.PositiveIntegerField(
        default=120,
        help_text="Maximum time in minutes that a blue team can spend securing a deployment (0 means no limit)"
    )
    max_red_team_time = models.PositiveIntegerField(
        default=0,
        help_text="Maximum time in minutes that a red team can spend attacking a deployment (0 means no limit)"
    )

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Session"
        verbose_name_plural = "Sessions"

    def __str__(self):
        return f"{self.name} ({self.status})"

    def is_active(self):
        """Check if session is currently active"""
        return self.status == GameSessionStatus.ACTIVE and self.start_date <= timezone.now() <= self.end_date

    def get_containers(self):
        """Get all containers associated with this session via team assignments"""
        from challenges.models.container import ChallengeContainer
        deployment_ids = self.team_assignments.values_list('deployment_id', flat=True).distinct()
        return ChallengeContainer.objects.filter(deployment_id__in=deployment_ids)

    @property
    def get_teams(self):
        """Get all teams participating in this session"""
        from accounts.models import Team
        return Team.objects.filter(assignments__session=self).distinct()

    def get_active_assignments(self):
        """Get currently active team assignments"""
        now = timezone.now()
        return self.team_assignments.filter(start_date__lte=now, end_date__gte=now)

    def get_max_time_for_role(self, role):
        """Get maximum time allowed for a specific team role"""
        if not self.enable_time_restrictions:
            return 0
        return self.max_blue_team_time if role == TeamRole.BLUE else self.max_red_team_time


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
            from ctf.services import FlagService
            from challenges.services import ContainerService
            instance.phases.all().update(status=GamePhaseStatus.COMPLETED)
            FlagService().distribute_uncaptured_flags_points(instance)
            ContainerService().stop_session_containers(instance)


class TeamAssignmentManager(models.Manager):
    def create(self, *args, **kwargs):
        entrypoint_container = kwargs.get('entrypoint_container', None)
        deployment = kwargs.get('deployment', None)
        if entrypoint_container is None and deployment is not None:
            entrypoints = [c for c in deployment.containers.all() if getattr(c, 'is_entrypoint', False)]
            if entrypoints:
                kwargs['entrypoint_container'] = random.choice(entrypoints)
            else:
                kwargs['entrypoint_container'] = None
        return super().create(**kwargs)


class TeamAssignment(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    session = models.ForeignKey(GameSession, on_delete=models.CASCADE, related_name="team_assignments")
    team = models.ForeignKey("accounts.Team", on_delete=models.CASCADE, related_name="assignments")
    deployment = models.ForeignKey("challenges.ChallengeDeployment", on_delete=models.CASCADE,
                                   related_name="assignments")
    entrypoint_container = models.ForeignKey("challenges.ChallengeContainer", on_delete=models.CASCADE,
                                             related_name="entrypoint_assignments", null=True)
    role = models.CharField(max_length=8, choices=TeamRole, default=TeamRole.BLUE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    objects = TeamAssignmentManager()

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

    def get_used_flag_hints(self) -> QuerySet[Flag]:
        """Get hints that have been used by the team"""
        return Flag.objects.filter(
            hint_usages__team=self.team,
            hint_usages__session=self.session
        ).order_by("points")

    def get_next_available_flag_hint(self) -> Flag:
        """Get the next available hint for this session (lowest points not yet used)"""
        used_flag_hints = self.get_used_flag_hints()
        deployment_flag_hints = Flag.objects.filter(container__deployment=self.deployment)

        if used_flag_hints.count() == deployment_flag_hints.count():
            return None

        for flag in used_flag_hints:
            deployment_flag_hints = deployment_flag_hints.exclude(Q(hint=flag.hint) | Q(is_captured=True))

        return deployment_flag_hints.order_by("points").first()
