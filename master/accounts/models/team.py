import uuid

from django.core.exceptions import ValidationError, PermissionDenied
from django.db import models


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
        ordering = ["name"]
        indexes = [
            models.Index(fields=['uuid']),
            models.Index(fields=['join_key']),
        ]
        verbose_name = "Global Settings"
        verbose_name_plural = "Global Settings"

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

    class Meta:
        ordering = ['-score', 'name']
