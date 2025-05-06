from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.shortcuts import redirect

from accounts.models import User, Team


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = ('username', 'email', 'team', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'team')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('email', 'ssh_public_key')}),
        ('Team info', {'fields': ('team',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    search_fields = ('username', 'email')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions',)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'user_count', 'score', 'created_at', 'is_in_game')
    readonly_fields = ('join_key', 'created_at')
    search_fields = ('name',)
    list_filter = ('is_in_game',)
    actions = ['set_teams_in_game', 'set_teams_not_in_game']
    change_list_template = "admin/team/change_list.html"

    @staticmethod
    def user_count(obj):
        return obj.users.count()

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                "set_all_in_game/",
                self.admin_site.admin_view(self.set_all_teams_in_game_view),
                name="team-set-all-in-game",
            ),
            path(
                "set_all_not_in_game/",
                self.admin_site.admin_view(self.set_all_teams_not_in_game_view),
                name="team-set-all-not-in-game",
            ),
        ]
        return custom_urls + urls

    def set_all_teams_in_game_view(self, request):
        """View to set all teams as in game"""
        updated = self.model.objects.update(is_in_game=True)
        self.message_user(request, f"All teams ({updated}) were successfully set as in game.")
        return redirect("admin:accounts_team_changelist")

    def set_all_teams_not_in_game_view(self, request):
        """View to set all teams as not in game"""
        updated = self.model.objects.update(is_in_game=False)
        self.message_user(request, f"All teams ({updated}) were successfully set as not in game.")
        return redirect("admin:accounts_team_changelist")

    def set_teams_in_game(self, request, queryset):
        updated = queryset.update(is_in_game=True)
        self.message_user(request, f"{updated} teams were successfully set as in game.")

    set_teams_in_game.short_description = "Set selected teams as in game"

    def set_teams_not_in_game(self, request, queryset):
        updated = queryset.update(is_in_game=False)
        self.message_user(request, f"{updated} teams were successfully set as not in game.")

    set_teams_not_in_game.short_description = "Set selected teams as not in game"
