from django.contrib import admin
from django.forms import Select
from django.shortcuts import redirect
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from ctf.forms.admin_forms import GameContainerForm
from ctf.models import *


def handle_action_redirect(request, container_id):
    """Helper to handle redirects from actions"""
    if request.META.get("HTTP_REFERER", "").endswith(f"/change/"):
        return redirect("admin:ctf_gamecontainer_change", container_id)
    return redirect("admin:ctf_gamecontainer_changelist")


class ScenarioTemplateAdmin(admin.ModelAdmin):
    list_display = ("folder", "name", "description")


class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "score", "red_points", "blue_points")


class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "team", "is_active")
    list_filter = ("is_active", "is_staff", "team")
    search_fields = ("username", "email")


class FlagInline(admin.TabularInline):
    model = Flag
    fields = ("points", "owner", "is_captured", "captured_by")
    readonly_fields = ("points", "owner", "is_captured", "captured_by")
    show_change_link = True
    extra = 0
    can_delete = False


class GameContainerAdmin(admin.ModelAdmin):
    form = GameContainerForm
    list_display = ("name", "status", "blue_team", "red_team", "container_actions")
    list_filter = ("status",)
    actions = ["sync_status", "start_containers", "stop_containers"]
    inlines = [FlagInline]

    fieldsets = (
        (None, {
            'fields': ('name', 'template_name', 'docker_id', 'status')
        }),
        ('Team Assignment', {
            'fields': ('blue_team', 'red_team', 'access_rotation_date')
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
        ]
        return custom_urls + urls

    def start_container_view(self, request, container_id):
        game_container = self.model.objects.get(pk=container_id)
        self.container_service.sync_container_status(game_container)
        if game_container.status == ContainerStatus.RUNNING:
            self.message_user(request, f"Container {game_container.name} is already running.", level="WARNING")
        elif self.container_service.start_container(game_container):
            self.message_user(request, f"Container {game_container.name} started successfully.")
        else:
            self.message_user(request, f"Failed to start container {game_container.name}.", level="ERROR")
        return handle_action_redirect(request, container_id)

    def stop_container_view(self, request, container_id):
        game_container = self.model.objects.get(pk=container_id)
        self.container_service.sync_container_status(game_container)
        if game_container.status == ContainerStatus.STOPPED:
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


class ContainerAccessLogAdmin(admin.ModelAdmin):
    """Admin interface for container access logs"""
    list_display = ('user', 'container', 'access_type', 'timestamp', 'ip_address', 'session_length')
    list_filter = ('access_type', 'container', 'user')
    search_fields = ('user__username', 'container__name', 'ip_address')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)


class GameSessionAdmin(admin.ModelAdmin):
    """Enhanced admin interface for game sessions"""
    list_display = ('name', 'status', 'start_date', 'end_date', 'is_active')
    list_filter = ('status',)
    search_fields = ('name',)

    def is_active(self, obj):
        return obj.is_active()

    is_active.boolean = True
    is_active.short_description = "Active"


class TeamAssignmentAdmin(admin.ModelAdmin):
    """Enhanced admin interface for team assignments"""
    list_display = ('team', 'container', 'role', 'session', 'start_date', 'end_date', 'is_active')
    list_filter = ('role', 'session')
    search_fields = ('team__name', 'container__name')

    def is_active(self, obj):
        return obj.is_active()

    is_active.boolean = True
    is_active.short_description = "Active"


admin.site.register(ScenarioTemplate, ScenarioTemplateAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(GameContainer, GameContainerAdmin)
admin.site.register(GameSession, GameSessionAdmin)
admin.site.register(TeamAssignment, TeamAssignmentAdmin)
admin.site.register(Flag, FlagAdmin)
admin.site.register(ContainerAccessLog, ContainerAccessLogAdmin)
