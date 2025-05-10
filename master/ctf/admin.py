import logging

from django.contrib import admin
from django.shortcuts import redirect
from django.utils import timezone

from accounts.models import Team
from ctf.forms.admin_forms import GameSessionForm
from ctf.models import Flag, GameSession, TeamAssignment, GamePhase, Badge
from ctf.models.enums import GameSessionStatus
from ctf.models.settings import GlobalSettings
from ctf.services import MatchmakingService

logger = logging.getLogger(__name__)


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    pass


class FlagInline(admin.TabularInline):
    model = Flag
    fields = ("points", "owner", "is_captured", "captured_by")
    readonly_fields = ("points", "owner", "is_captured", "captured_by")
    show_change_link = True
    extra = 0
    can_delete = False
    fk_name = 'container'


@admin.register(Flag)
class FlagAdmin(admin.ModelAdmin):
    list_display = ("value", "owner", "container", "points", "is_captured", "captured_by", "captured_at")
    list_filter = ("is_captured", "owner", "container")
    search_fields = ("value", "placeholder")
    fieldsets = (
        (None, {
            'fields': ('value', 'points', 'placeholder', 'hint')
        }),
        ('Relationships', {
            'fields': ('container', 'owner'),
            'classes': ('wide',)
        }),
        ('Capture Status', {
            'fields': ('is_captured', 'captured_by', 'captured_at'),
            'classes': ('wide',)
        }),
    )
    readonly_fields = ('captured_at',)

    def get_queryset(self, request):
        """Ensure container and owner are prefetched for efficiency"""
        queryset = super().get_queryset(request)
        return queryset.select_related('container', 'owner', 'captured_by')


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    form = GameSessionForm
    list_display = ('name', 'status', 'template', 'start_date', 'end_date', 'is_active')
    list_filter = ('status',)
    search_fields = ('name',)
    readonly_fields = ('end_date',)

    def is_active(self, obj):
        return obj.is_active()

    is_active.boolean = True
    is_active.short_description = "Active"

    def save_model(self, request, obj, form, change):
        """Override save_model to handle session creation"""
        try:
            if not change:
                if obj.status == GameSessionStatus.ACTIVE:
                    obj.start_date = timezone.now()
                    super().save_model(request, obj, form, change)

                    matchmaking_service = MatchmakingService()
                    teams = Team.objects.filter(is_in_game=True)

                    if teams:
                        success = matchmaking_service.create_round_assignments(obj, teams)
                        if success:
                            self.message_user(request, f"Successfully prepared first round for session {obj.name}")
                        else:
                            self.message_user(request, f"Failed to prepare first round for session {obj.name}",
                                              level="ERROR")
                    else:
                        self.message_user(request,
                                          f"No teams found for session {obj.name}. Add teams to the game before assigning them.",
                                          level="WARNING")
                else:
                    super().save_model(request, obj, form, change)
            else:
                super().save_model(request, obj, form, change)
        except Exception as e:
            logger.error(f"Error creating game session: {e}")
            self.message_user(request, f"Failed to create session: {str(e)}", level="ERROR")
            if not change and obj.id is not None:
                obj.delete()


@admin.register(TeamAssignment)
class TeamAssignmentAdmin(admin.ModelAdmin):
    """Enhanced admin interface for team assignments"""
    list_display = ('team', 'deployment', 'role', 'session', 'start_date', 'end_date', 'is_active')
    list_filter = ('role', 'session')
    search_fields = ('team__name', 'deployment_pk')

    def is_active(self, obj):
        return obj.is_active()

    is_active.boolean = True
    is_active.short_description = "Active"


@admin.register(GamePhase)
class GamePhaseAdmin(admin.ModelAdmin):
    """Admin interface for managing game rounds"""
    list_display = ('phase_name', 'session', 'session__template', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'session')
    ordering = ('session', 'phase_name', 'start_date', 'end_date')

    def get_phase(self, obj):
        return obj.get_phase() or 'N/A'

    get_phase.short_description = 'Current Phase'


@admin.register(GlobalSettings)
class GlobalSettingsAdmin(admin.ModelAdmin):
    change_form_template = 'admin/ctf/globalsettings/change_form.html'
    object_history_template = 'admin/ctf/globalsettings/object_history.html'

    verbose_name_plural = "Global System Settings"

    fieldsets = (
        ('Team Settings', {
            'fields': ('max_team_size', 'number_of_tiers', 'allow_team_changes'),
            'classes': ('wide',),
        }),
        ('Container Settings', {
            'fields': ('enable_auto_container_shutdown', 'inactive_container_timeout'),
            'classes': ('wide',),
        }),
        ('Matchmaking Settings', {
            'fields': ('previous_targets_check_count',),
            'classes': ('wide',),
        })
    )

    def has_add_permission(self, request):
        return not GlobalSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        """Override changelist view to redirect to the settings form"""
        obj, created = GlobalSettings.objects.get_or_create(pk=1)
        return redirect('admin:ctf_globalsettings_change', obj.id)

    def response_post_save_change(self, request, obj):
        """Stay on the same page after saving"""
        return redirect('admin:ctf_globalsettings_change', obj.id)

    def get_urls(self):
        """Add custom URL patterns"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('', self.changelist_view, name='ctf_globalsettings_changelist'),
        ]
        return custom_urls + urls
