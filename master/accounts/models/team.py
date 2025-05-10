import uuid

from django.core.exceptions import ValidationError, PermissionDenied
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from ctf.models import Badge


class Team(models.Model):
    name = models.CharField(max_length=128)
    join_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    score = models.IntegerField(default=0)
    red_points = models.IntegerField(default=0)
    blue_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='created_teams')
    is_in_game = models.BooleanField(default=False)

    class Meta:
        ordering = ["-score", "name"]
        indexes = [
            models.Index(fields=['uuid']),
            models.Index(fields=['join_key']),
        ]
        verbose_name = "Team"
        verbose_name_plural = "Teams"

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
        TeamScoreHistory.record_score(self)

    def can_join(self):
        """Check if team can accept new members"""
        if self.is_in_game:
            return False
        from ctf.models.settings import GlobalSettings
        settings = GlobalSettings.get_settings()
        if not settings.allow_team_changes:
            return False
        return self.users.count() < settings.max_team_size

    def can_manage_members(self, user):
        """Check if user can manage team members"""
        if self.is_in_game:
            return False
        return user == self.created_by

    def all_members_have_ssh_keys(self):
        """Check if all team members have SSH keys set up"""
        return all(user.ssh_public_key.strip() for user in self.users.all())

    def should_be_in_game(self):
        """Check if team should be set as in game"""
        from ctf.models.settings import GlobalSettings
        settings = GlobalSettings.get_settings()
        return (self.users.count() == settings.max_team_size and
                self.all_members_have_ssh_keys())

    def remove_member(self, user, member_to_remove):
        """Remove a member from the team"""
        if not self.can_manage_members(user):
            raise PermissionDenied("You don't have permission to manage team members")

        if self.is_in_game:
            raise ValidationError("Cannot remove members while team is in a game")

        if member_to_remove == self.created_by:
            raise ValidationError("Cannot remove the team creator")

        if member_to_remove.team != self:
            raise ValidationError("User is not a member of this team")

        member_to_remove.team = None
        member_to_remove.save()

    def clean(self):
        """Validate team size"""
        from ctf.models.settings import GlobalSettings
        settings = GlobalSettings.get_settings()
        if self.pk:
            if self.users.count() > settings.max_team_size:
                raise ValidationError(f"Team cannot have more than {settings.max_team_size} members")
            if self.should_be_in_game():
                self.is_in_game = True


@receiver(pre_save, sender=Team)
def track_points_changes(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_team = Team.objects.get(pk=instance.pk)
            instance._old_score = old_team.score
            instance._old_blue_points = old_team.blue_points
            instance._old_red_points = old_team.red_points
        except Team.DoesNotExist:
            instance._old_score = None
            instance._old_blue_points = None
            instance._old_red_points = None
    else:
        instance._old_score = None
        instance._old_blue_points = None
        instance._old_red_points = None


@receiver(post_save, sender=Team)
def update_team_badges(sender, instance, **kwargs):
    if not instance.is_in_game:
        return

    old_score = getattr(instance, '_old_score', None)
    old_blue = getattr(instance, '_old_blue_points', None)
    old_red = getattr(instance, '_old_red_points', None)

    if (old_score is not None and old_score != instance.score) or \
            (old_blue is not None and old_blue != instance.blue_points) or \
            (old_red is not None and old_red != instance.red_points):

        Badge.update_team_badges(instance)

        if old_score is not None and old_score != instance.score:
            teams_to_check = Team.objects.filter(
                is_in_game=True,
                score__gte=min(old_score, instance.score),
                score__lte=max(old_score, instance.score)
            ).exclude(id=instance.id)
        elif old_blue is not None and old_blue != instance.blue_points:
            teams_to_check = Team.objects.filter(
                is_in_game=True,
                blue_points__gte=min(old_blue, instance.blue_points),
                blue_points__lte=max(old_blue, instance.blue_points)
            ).exclude(id=instance.id)
        elif old_red is not None and old_red != instance.red_points:
            teams_to_check = Team.objects.filter(
                is_in_game=True,
                red_points__gte=min(old_red, instance.red_points),
                red_points__lte=max(old_red, instance.red_points)
            ).exclude(id=instance.id)
        else:
            teams_to_check = Team.objects.none()

        for team in teams_to_check:
            Badge.update_team_badges(team)


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
