import logging

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.forms import Select
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from ctf.forms.admin_forms import GameContainerForm, GameSessionForm
from ctf.models import *
from ctf.models.enums import ContainerStatus, GameSessionStatus
from ctf.models.settings import GlobalSettings
from ctf.services import DockerService, ContainerService, MatchmakingService

logger = logging.getLogger(__name__)


def handle_action_redirect(request, container_id):
    """Helper to handle redirects from actions"""
    if request.META.get("HTTP_REFERER", "").endswith(f"/change/"):
        return redirect("admin:ctf_gamecontainer_change", container_id)
    return redirect("admin:ctf_gamecontainer_changelist")


@admin.register(ChallengeTemplate)
class ChallengeTemplateAdmin(admin.ModelAdmin):
    list_display = ("folder", "name", "description")
    actions = ["sync_templates"]
    change_list_template = "admin/ctf/challengetemplate/change_list.html"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                "sync/",
                self.admin_site.admin_view(self.sync_templates_view),
                name="challengetemplate-sync",
            ),
        ]
        return custom_urls + urls

    def sync_templates_view(self, request):
        """View to handle template sync"""
        from django.core.management import call_command
        try:
            call_command("sync_templates")
            self.message_user(request, "Templates synced successfully.")
        except Exception as e:
            self.message_user(request, f"Error syncing templates: {str(e)}", level="ERROR")
        return redirect("admin:ctf_challengetemplate_changelist")

    def sync_templates(self, request):
        """Action to sync templates"""
        return self.sync_templates_view(request)

    sync_templates.short_description = "Sync templates from filesystem"


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


class FlagInline(admin.TabularInline):
    model = Flag
    fields = ("points", "owner", "is_captured", "captured_by")
    readonly_fields = ("points", "owner", "is_captured", "captured_by")
    show_change_link = True
    extra = 0
    can_delete = False
    fk_name = 'container'


@admin.register(GameContainer)
class GameContainerAdmin(admin.ModelAdmin):
    form = GameContainerForm
    list_display = ("name", "status", "blue_team", "red_team", "is_entrypoint", "container_actions")
    list_filter = ("status",)
    actions = ["sync_status", "start_containers", "stop_containers"]
    inlines = [FlagInline]
    change_list_template = "admin/ctf/gamecontainer/change_list.html"

    fieldsets = (
        (None, {
            'fields': ('name', 'template_name', 'docker_id', 'status')
        }),
        ('Team Assignment', {
            'fields': ('blue_team', 'red_team')
        }),
        ('Services', {
            'fields': ('services',)
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize services
        self.docker_service = DockerService()
        self.container_service = ContainerService(self.docker_service)

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == "status":
            # Only add buttons if we're editing an existing object
            if kwargs.get("request").resolver_match.kwargs.get("object_id"):
                object_id = kwargs.get("request").resolver_match.kwargs.get("object_id")
                formfield.widget = StatusWidgetWithButtons(object_id)
        return formfield

    def container_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Start</a>&nbsp;' '<a class="button" href="{}">Stop</a>&nbsp;' '<a class="button" href="{}">Sync</a>',
            f"/admin/ctf/gamecontainer/{obj.pk}/start/",
            f"/admin/ctf/gamecontainer/{obj.pk}/stop/",
            f"/admin/ctf/gamecontainer/{obj.pk}/sync/",
        )

    container_actions.short_description = "Actions"

    def sync_status(self, request, queryset):
        updated = 0
        for game_container in queryset:
            if self.container_service.sync_container_status(game_container):
                updated += 1
        self.message_user(request, f"Successfully synced status for {updated} of {queryset.count()} containers.")

    sync_status.short_description = "Sync selected containers' status"

    def start_containers(self, request, queryset):
        started = 0
        for game_container in queryset:
            if self.container_service.start_container(game_container):
                started += 1
        self.message_user(request, f"Successfully started {started} of {queryset.count()} containers.")

    start_containers.short_description = "Start selected containers"

    def stop_containers(self, request, queryset):
        stopped = 0
        for game_container in queryset:
            if self.container_service.stop_container(game_container):
                stopped += 1
        self.message_user(request, f"Successfully stopped {stopped} of {queryset.count()} containers.")

    stop_containers.short_description = "Stop selected containers"

    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:container_id>/start/",
                self.admin_site.admin_view(self.start_container_view),
                name="gamecontainer-start",
            ),
            path(
                "<int:container_id>/stop/",
                self.admin_site.admin_view(self.stop_container_view),
                name="gamecontainer-stop",
            ),
            path(
                "<int:container_id>/sync/",
                self.admin_site.admin_view(self.sync_container_view),
                name="gamecontainer-sync",
            ),
            path(
                "sync_all/",
                self.admin_site.admin_view(self.sync_all_view),
                name="gamecontainer-sync-all",
            ),
            path(
                "stop_all/",
                self.admin_site.admin_view(self.stop_all_view),
                name="gamecontainer-stop-all",
            ),
            path(
                "start_all/",
                self.admin_site.admin_view(self.start_all_view),
                name="gamecontainer-start-all",
            ),
        ]
        return custom_urls + urls

    def start_container_view(self, request, container_id):
        game_container: GameContainer = self.model.objects.get(pk=container_id)
        self.container_service.sync_container_status(game_container)
        if game_container.is_running():
            self.message_user(request, f"Container {game_container.name} is already running.", level="WARNING")
        elif self.container_service.start_container(game_container):
            self.message_user(request, f"Container {game_container.name} started successfully.")
        else:
            self.message_user(request, f"Failed to start container {game_container.name}.", level="ERROR")
        return handle_action_redirect(request, container_id)

    def stop_container_view(self, request, container_id):
        game_container = self.model.objects.get(pk=container_id)
        self.container_service.sync_container_status(game_container)
        if game_container.is_stopped():
            self.message_user(request, f"Container {game_container.name} is already stopped.", level="WARNING")
        elif self.container_service.stop_container(game_container):
            self.message_user(request, f"Container {game_container.name} stopped successfully.")
        else:
            self.message_user(request, f"Failed to stop container {game_container.name}.", level="ERROR")
        return handle_action_redirect(request, container_id)

    def sync_container_view(self, request, container_id):
        game_container = self.model.objects.get(pk=container_id)
        if self.container_service.sync_container_status(game_container):
            self.message_user(request, f"Container {game_container.name} status synced successfully.")
        else:
            self.message_user(request, f"Failed to sync container {game_container.name} status.", level="ERROR")
        return handle_action_redirect(request, container_id)

    def sync_all_view(self, request):
        """View to sync all containers"""
        synced = 0
        failed = 0
        for game_container in self.model.objects.all():
            if self.container_service.sync_container_status(game_container):
                synced += 1
            else:
                failed += 1

        if failed:
            self.message_user(request, f"Synced {synced} containers. Failed to sync {failed} containers.",
                              level="WARNING")
        else:
            self.message_user(request, f"Successfully synced all {synced} containers.")
        return redirect("admin:ctf_gamecontainer_changelist")

    def stop_all_view(self, request):
        """View to stop all containers"""
        stopped = 0
        failed = 0
        for game_container in self.model.objects.all():
            if self.container_service.stop_container(game_container):
                stopped += 1
            else:
                failed += 1

        if failed:
            self.message_user(request, f"Stopped {stopped} containers. Failed to stop {failed} containers.",
                              level="WARNING")
        else:
            self.message_user(request, f"Successfully stopped all {stopped} containers.")
        return redirect("admin:ctf_gamecontainer_changelist")

    def start_all_view(self, request):
        """View to start all containers"""
        started = 0
        failed = 0
        for game_container in self.model.objects.all():
            if self.container_service.start_container(game_container):
                started += 1
            else:
                failed += 1

        if failed:
            self.message_user(request, f"Started {started} containers. Failed to start {failed} containers.",
                              level="WARNING")
        else:
            self.message_user(request, f"Successfully started all {started} containers.")
        return redirect("admin:ctf_gamecontainer_changelist")

    def has_delete_permission(self, request, obj=None):
        """Override delete permission to ensure proper cleanup"""
        if obj and obj.status == ContainerStatus.RUNNING:
            return False
        return super().has_delete_permission(request, obj)

    def delete_model(self, request, obj):
        """Override delete_model to ensure proper cleanup"""
        if self.container_service.delete_game_container(obj):
            self.message_user(request, f"Container {obj.name} successfully deleted.")
        else:
            self.message_user(request, f"Failed to delete container {obj.name}. Check logs for details.", level="ERROR")

    def delete_queryset(self, request, queryset):
        """Override delete_queryset to ensure proper cleanup for bulk deletions"""
        for obj in queryset:
            self.delete_model(request, obj)

    def save_model(self, request, obj, form, change):
        """Override save_model to ensure status is synced before saving"""
        if change:
            self.container_service.sync_container_status(obj)
        super().save_model(request, obj, form, change)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """Override change_view to sync status before displaying the form"""
        obj = self.get_object(request, object_id)
        if obj:
            self.container_service.sync_container_status(obj)
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def changelist_view(self, request, extra_context=None):
        """Override changelist_view to sync all container statuses"""
        if "sync_all" in request.GET:
            for game_container in self.model.objects.all():
                self.container_service.sync_container_status(game_container)
        return super().changelist_view(request, extra_context=extra_context)

    class Media:
        css = {"all": ("admin/css/container_admin.css",)}


class StatusWidgetWithButtons(Select):
    def __init__(self, object_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.object_id = object_id
        try:
            game_container = GameContainer.objects.get(pk=object_id)
            self.choices = ContainerStatus
            self.value = game_container.status
        except GameContainer.DoesNotExist:
            self.choices = []
            self.value = None

    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}

        attrs["disabled"] = "disabled"
        value = self.value if self.value is not None else value
        html = super().render(name, value, attrs, renderer)
        buttons = format_html(
            '<div class="status-actions" style="display: inline-block; margin-left: 10px;">' '<a class="button" href="{}">Start</a>&nbsp;' '<a class="button" href="{}">Stop</a>&nbsp;' '<a class="button" href="{}">Sync</a>' '<input type="hidden" name="{}" value="{}">' "</div>",
            f"/admin/ctf/gamecontainer/{self.object_id}/start/",
            f"/admin/ctf/gamecontainer/{self.object_id}/stop/",
            f"/admin/ctf/gamecontainer/{self.object_id}/sync/",
            name,
            value or "",
        )

        return mark_safe(f'<div style="display: flex; align-items: center;">{html}{buttons}</div>')


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


@admin.register(ContainerAccess)
class ContainerAccessAdmin(admin.ModelAdmin):
    """Admin interface for container access logs"""
    list_display = ('user', 'container', 'access_type', 'start_time', 'ip_address', 'session_length')
    list_filter = ('access_type', 'container', 'user')
    search_fields = ('user__username', 'container__name', 'ip_address')
    date_hierarchy = 'start_time'
    readonly_fields = ('start_time',)


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
    search_fields = ('team__name', 'deployment__pk')

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
    list_display = ('max_team_size', 'allow_team_changes')
    readonly_fields = ('id',)

    def has_add_permission(self, request):
        return not GlobalSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'user_count', 'score', 'created_at', 'is_in_game')
    readonly_fields = ('join_key', 'created_at')
    search_fields = ('name',)
    list_filter = ('is_in_game',)
    actions = ['set_teams_in_game', 'set_teams_not_in_game']
    change_list_template = "admin/ctf/team/change_list.html"

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
        return redirect("admin:ctf_team_changelist")

    def set_all_teams_not_in_game_view(self, request):
        """View to set all teams as not in game"""
        updated = self.model.objects.update(is_in_game=False)
        self.message_user(request, f"All teams ({updated}) were successfully set as not in game.")
        return redirect("admin:ctf_team_changelist")

    def set_teams_in_game(self, request, queryset):
        updated = queryset.update(is_in_game=True)
        self.message_user(request, f"{updated} teams were successfully set as in game.")

    set_teams_in_game.short_description = "Set selected teams as in game"

    def set_teams_not_in_game(self, request, queryset):
        updated = queryset.update(is_in_game=False)
        self.message_user(request, f"{updated} teams were successfully set as not in game.")

    set_teams_not_in_game.short_description = "Set selected teams as not in game"


@admin.register(ChallengeDeployment)
class ChallengeDeploymentAdmin(admin.ModelAdmin):
    list_display = ('pk', 'get_template_name')
    list_filter = ('template',)

    def get_template_name(self, obj):
        return obj.template.name if obj.template else "No template"

    get_template_name.short_description = "Template"


@admin.register(ChallengeNetworkConfig)
class ChallengeNetworkConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'subnet', 'template', 'deployment_id', 'containers_count')
    list_filter = ('template',)
    search_fields = ('name', 'subnet')
    readonly_fields = ('subnet',)
    actions = ['clean_network']
    change_list_template = "admin/ctf/challengenetworkconfig/change_list.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docker_service = DockerService()

    def containers_count(self, obj):
        return obj.containers.count()

    containers_count.short_description = "Containers"

    def has_delete_permission(self, request, obj=None):
        """Check if network can be deleted"""
        if obj and obj.containers.exists():
            connected_containers = obj.containers.filter(status=ContainerStatus.RUNNING)
            if connected_containers.exists():
                return False
        return super().has_delete_permission(request, obj)

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                "clean_all_networks/",
                self.admin_site.admin_view(self.clean_all_networks_view),
                name="challengenetworkconfig-clean-all",
            ),
        ]
        return custom_urls + urls

    def clean_all_networks_view(self, request):
        """View to clean all unused Docker networks"""
        try:
            self.docker_service.clean_networks()
            self.message_user(request, "All unused Docker networks cleaned successfully.")
        except Exception as e:
            logger.error(f"Error cleaning Docker networks: {str(e)}")
            self.message_user(request, f"Error cleaning Docker networks: {str(e)}", level="ERROR")
        return redirect("admin:ctf_challengenetworkconfig_changelist")

    def clean_network(self, request, queryset):
        """Action to clean a specific network"""
        deleted = 0
        failed = 0

        for network_config in queryset:
            try:
                # Find the Docker network by name/subnet
                docker_networks = self.docker_service.list_networks()
                for network in docker_networks:
                    if network.attrs.get("IPAM") and network.attrs["IPAM"].get("Config"):
                        for config in network.attrs["IPAM"]["Config"]:
                            if "Subnet" in config and config["Subnet"].startswith(network_config.subnet):
                                if self.docker_service.remove_network(network):
                                    deleted += 1
                                else:
                                    failed += 1
            except Exception as e:
                logger.error(f"Failed to delete network {network_config.name}: {e}")
                failed += 1

        if failed:
            self.message_user(
                request, f"Deleted {deleted} networks. Failed to delete {failed} networks.", level="WARNING"
            )
        else:
            self.message_user(request, f"Successfully deleted {deleted} networks.")

    clean_network.short_description = "Delete selected Docker networks"

    def delete_queryset(self, request, queryset):
        """Handle bulk deletions by removing each network individually"""
        networks_deleted = 0
        networks_failed = 0
        networks_not_found = 0

        # Get all Docker networks once to avoid repeated API calls
        docker_networks = self.docker_service.list_networks()

        for obj in queryset:
            try:
                network_deleted = False

                for network in docker_networks:
                    if network.attrs.get("IPAM") and network.attrs["IPAM"].get("Config"):
                        for config in network.attrs["IPAM"]["Config"]:
                            if "Subnet" in config and config["Subnet"].startswith(obj.subnet):
                                if self.docker_service.remove_network(network):
                                    networks_deleted += 1
                                    network_deleted = True
                                else:
                                    networks_failed += 1
                                break

                if not network_deleted:
                    networks_not_found += 1
            except Exception as e:
                logger.error(f"Failed to delete Docker network for {obj.name} ({obj.subnet}): {e}")
                networks_failed += 1

        # Now delete all the Django models
        super().delete_queryset(request, queryset)

        # Report results
        if networks_deleted > 0:
            self.message_user(request, f"Successfully deleted {networks_deleted} Docker networks.")

        if networks_failed > 0:
            self.message_user(request, f"Failed to delete {networks_failed} Docker networks.", level="ERROR")

        if networks_not_found > 0:
            self.message_user(request, f"{networks_not_found} Docker networks were not found.", level="WARNING")

    def delete_model(self, request, obj):
        """Delete the Docker network when the model is deleted"""
        try:
            network_deleted = False
            docker_networks = self.docker_service.list_networks()

            for network in docker_networks:
                if network.attrs.get("IPAM") and network.attrs["IPAM"].get("Config"):
                    for config in network.attrs["IPAM"]["Config"]:
                        if "Subnet" in config and config["Subnet"].startswith(obj.subnet):
                            if self.docker_service.remove_network(network):
                                network_deleted = True
                                self.message_user(request,
                                                  f"Docker network for {obj.name} ({obj.subnet}) successfully deleted.")
                            else:
                                self.message_user(request,
                                                  f"Failed to delete Docker network for {obj.name} ({obj.subnet}).",
                                                  level="WARNING")
                            break

            if not network_deleted:
                self.message_user(request, f"No matching Docker network found for {obj.name} ({obj.subnet}).",
                                  level="WARNING")

            # Delete the Django model
            super().delete_model(request, obj)
        except Exception as e:
            logger.error(f"Failed to delete Docker network for {obj.name} ({obj.subnet}): {e}")
            self.message_user(request, f"Failed to delete Docker network: {e}", level="ERROR")
            # Still delete the Django model even if Docker network deletion fails
            super().delete_model(request, obj)
