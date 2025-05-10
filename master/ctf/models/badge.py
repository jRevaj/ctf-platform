from django.db import models
from django.db.transaction import atomic


class Badge(models.Model):
    BADGE_TYPES = [
        ('overall', 'Overall'),
        ('blue', 'Blue Team'),
        ('red', 'Red Team'),
        ('custom', 'Custom'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    icon_class = models.CharField(max_length=50, help_text="CSS class for the badge icon")
    badge_type = models.CharField(max_length=20, choices=BADGE_TYPES, default='custom')
    team = models.ForeignKey('accounts.Team', on_delete=models.SET_NULL, null=True, blank=True, related_name='badges')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Badge"
        verbose_name_plural = "Badges"
        ordering = ['badge_type', 'name']

    def __str__(self):
        return self.name

    @classmethod
    def get_badge_by_type(cls, badge_type):
        """Get badge by type"""
        return cls.objects.filter(badge_type=badge_type).first()

    @classmethod
    @atomic
    def update_team_badges(cls, team):
        """Update badges for a specific team"""
        if not team.is_in_game:
            return

        with atomic():
            badges = cls.objects.select_for_update().filter(
                badge_type__in=['overall', 'blue', 'red']
            )

            teams = team.__class__.objects.select_for_update().filter(is_in_game=True)

            overall_badge = next((b for b in badges if b.badge_type == 'overall'), None)
            if overall_badge:
                best_overall = teams.order_by('-score').first()
                if best_overall and best_overall.id == team.id:
                    overall_badge.team = team
                    overall_badge.save()

            blue_badge = next((b for b in badges if b.badge_type == 'blue'), None)
            if blue_badge:
                best_blue = teams.order_by('-blue_points').first()
                if best_blue and best_blue.id == team.id:
                    blue_badge.team = team
                    blue_badge.save()

            red_badge = next((b for b in badges if b.badge_type == 'red'), None)
            if red_badge:
                best_red = teams.order_by('-red_points').first()
                if best_red and best_red.id == team.id:
                    red_badge.team = team
                    red_badge.save()
