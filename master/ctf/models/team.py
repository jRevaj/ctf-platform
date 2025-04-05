import uuid

from django.core.exceptions import ValidationError, PermissionDenied
from django.db import models

from ctf.models.settings import GlobalSettings


class Team(models.Model):
    name = models.CharField(max_length=128)
    join_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    score = models.IntegerField(default=0)
    red_points = models.IntegerField(default=0)
    blue_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('ctf.User', on_delete=models.SET_NULL, null=True, related_name='created_teams')
    is_in_game = models.BooleanField(default=False)

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
        settings = GlobalSettings.get_settings()
        if not settings.allow_team_changes:
            return False
        return self.users.count() < settings.max_team_size

    def can_manage_members(self, user):
        """Check if user can manage team members"""
        if self.is_in_game:
            return False
        return user == self.created_by

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
        settings = GlobalSettings.get_settings()
        # Only check team size if the team is already saved
        if self.pk:
            if self.users.count() > settings.max_team_size:
                raise ValidationError(f"Team cannot have more than {settings.max_team_size} members")

    class Meta:
        ordering = ['-score', 'name']
