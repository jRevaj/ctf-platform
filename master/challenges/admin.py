import logging

from django.contrib import admin
from django.forms import Select
from django.shortcuts import redirect
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from challenges.forms.admin_forms import ChallengeTemplateForm, ChallengeContainerForm
from challenges.models import ChallengeTemplate, ChallengeContainer, DeploymentAccess, ChallengeDeployment, \
    ChallengeNetworkConfig
from challenges.models.enums import ContainerStatus
from challenges.services import DockerService, ContainerService
from ctf.admin import FlagInline
from ctf.utils.admin_utils import handle_action_redirect

logger = logging.getLogger(__name__)


@admin.register(ChallengeTemplate)
class ChallengeTemplateAdmin(admin.ModelAdmin):
    form = ChallengeTemplateForm
    list_display = ("folder", "name", "title", "description")
    actions = ["sync_templates"]
    change_list_template = "admin/challengetemplate/change_list.html"
    readonly_fields = ('folder',)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj:
            form.base_fields['template_file'].help_text = "Upload a new zip file to replace the existing scenario"
        return form

    def delete_model(self, request, obj):
        """Override delete_model to ensure template folder is deleted"""
        try:
            obj.delete()
            self.message_user(request, "Template and its folder were successfully deleted.")
        except Exception as e:
            self.message_user(request, f"Error deleting template: {str(e)}", level="ERROR")

    def delete_queryset(self, request, queryset):
        """Override delete_queryset to handle bulk deletions"""
        for obj in queryset:
            try:
                obj.delete()
            except Exception as e:
                self.message_user(request, f"Error deleting template {obj}: {str(e)}", level="ERROR")
        self.message_user(request, "Selected templates were successfully deleted.")

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
            call_command("sync_templates", "--all")
            self.message_user(request, "Templates synced successfully.")
        except Exception as e:
            self.message_user(request, f"Error syncing templates: {str(e)}", level="ERROR")
        return redirect("admin:challenges_challengetemplate_changelist")

    def sync_templates(self, request):
        """Action to sync templates"""
        return self.sync_templates_view(request)

    sync_templates.short_description = "Sync templates from filesystem"


@admin.register(ChallengeContainer)
class ChallengeContainerAdmin(admin.ModelAdmin):
    form = ChallengeContainerForm
    list_display = ("name", "status", "blue_team", "red_team", "is_entrypoint", "container_actions")
    list_filter = ("status",)
    actions = ["sync_status", "start_containers", "stop_containers"]
    inlines = [FlagInline]
    change_list_template = "admin/challengecontainer/change_list.html"

    fieldsets = (
        (None, {
            'fields': ('name', 'template_name', 'docker_id', 'status', 'port')
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
        self.docker_service = DockerService()
        self.container_service = ContainerService(self.docker_service)

    @staticmethod
    def container_actions(obj):
        return format_html(
            '<a class="button" href="{}">Start</a>&nbsp;'
            '<a class="button" href="{}">Stop</a>&nbsp;'
            '<a class="button" href="{}">Sync</a>',
            f"/admin/challengecontainer/{obj.pk}/action/start/",
            f"/admin/challengecontainer/{obj.pk}/action/stop/",
            f"/admin/challengecontainer/{obj.pk}/action/sync/",
        )

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:container_id>/action/<str:action>/",
                self.admin_site.admin_view(self.container_action_view),
                name="challengecontainer-action",
            ),
            path(
                "sync_all/",
                self.admin_site.admin_view(self.sync_all_view),
                name="challengecontainer-sync-all",
            ),
            path(
                "stop_all/",
                self.admin_site.admin_view(self.stop_all_view),
                name="challengecontainer-stop-all",
            ),
            path(
                "start_all/",
                self.admin_site.admin_view(self.start_all_view),
                name="challengecontainer-start-all",
            ),
            path(
                "clean_orphaned/",
                self.admin_site.admin_view(self.clean_orphaned_view),
                name="challengecontainer-clean-orphaned",
            ),
        ]
        return custom_urls + urls

    def container_action_view(self, request, container_id, action):
        game_container = self.model.objects.get(pk=container_id)
        self.container_service.sync_container_status(game_container)

        action_map = {
            'start': (self.container_service.start_container, 'started', 'running'),
            'stop': (self.container_service.stop_container, 'stopped', 'stopped'),
            'sync': (self.container_service.sync_container_status, 'synced', None)
        }

        if action not in action_map:
            self.message_user(request, f"Invalid action: {action}", level="ERROR")
            return handle_action_redirect(request, container_id)

        service_method, success_msg, check_status = action_map[action]

        if check_status and getattr(game_container, f"is_{check_status}")():
            self.message_user(request, f"Container {game_container.name} is already {check_status}.", level="WARNING")
        elif service_method(game_container):
            self.message_user(request, f"Container {game_container.name} {success_msg} successfully.")
        else:
            self.message_user(request, f"Failed to {action} container {game_container.name}.", level="ERROR")

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
        return redirect("admin:challenges_challengecontainer_changelist")

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
        return redirect("admin:challenges_challengecontainer_changelist")

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
        return redirect("admin:challenges_challengecontainer_changelist")

    def delete_model(self, request, obj):
        """Override delete_model to ensure proper cleanup"""
        if obj.delete():
            self.message_user(request, f"Container {obj.name} successfully deleted.")
        else:
            self.message_user(request, f"Failed to delete container {obj.name}. Check logs for details.", level="ERROR")

    def delete_queryset(self, request, queryset):
        """Override delete_queryset to ensure proper cleanup for bulk deletions"""
        success_count = 0
        fail_count = 0

        for obj in queryset:
            if obj.delete():
                success_count += 1
            else:
                fail_count += 1

        if success_count:
            self.message_user(request, f"Successfully deleted {success_count} containers.")
        if fail_count:
            self.message_user(request, f"Failed to delete {fail_count} containers. Check logs for details.",
                              level="ERROR")

    def save_model(self, request, obj, form, change):
        if change:
            self.container_service.sync_container_status(obj)
        super().save_model(request, obj, form, change)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        obj = self.get_object(request, object_id)
        if obj:
            self.container_service.sync_container_status(obj)
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def clean_orphaned_view(self, request):
        """View to clean orphaned containers"""
        try:
            cleaned_count = self.container_service.clean_docker_containers()
            self.message_user(request, f"Successfully cleaned {cleaned_count} orphaned containers.")
        except Exception as e:
            logger.error(f"Error cleaning orphaned containers: {e}")
            self.message_user(request, f"Error cleaning orphaned containers: {str(e)}", level="ERROR")
        return redirect("admin:challenges_challengecontainer_changelist")


class StatusWidgetWithButtons(Select):
    def __init__(self, object_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.object_id = object_id
        try:
            game_container = ChallengeContainer.objects.get(pk=object_id)
            self.choices = ContainerStatus
            self.value = game_container.status
        except ChallengeContainer.DoesNotExist:
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
            f"/admin/challengecontainer/{self.object_id}/start/",
            f"/admin/challengecontainer/{self.object_id}/stop/",
            f"/admin/challengecontainer/{self.object_id}/sync/",
            name,
            value or "",
        )

        return mark_safe(f'<div style="display: flex; align-items: center;">{html}{buttons}</div>')


@admin.register(DeploymentAccess)
class DeploymentAccessAdmin(admin.ModelAdmin):
    list_display = ('id', 'deployment', 'team', 'access_type', 'start_time', 'end_time', 'is_active',
                    'duration_display')
    list_filter = ('is_active', 'access_type', 'team')
    search_fields = ('deployment__id', 'session_id', 'team__name')
    date_hierarchy = 'start_time'
    readonly_fields = ('duration_display',)

    def duration_display(self, obj):
        if not obj.duration:
            return "N/A"

        total_seconds = obj.duration.total_seconds()
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

    duration_display.short_description = "Duration"


@admin.register(ChallengeDeployment)
class ChallengeDeploymentAdmin(admin.ModelAdmin):
    list_display = ('template', 'blue_team', 'red_team', 'last_activity', 'total_blue_access_time',
                    'total_red_access_time', 'has_active_connections', 'deployment_actions')
    list_filter = ('has_active_connections',)
    actions = ['start_containers', 'stop_containers', 'sync_container_status']
    change_list_template = "admin/challengedeployment/change_list.html"

    def delete_model(self, request, obj):
        """Override delete_model to ensure proper cleanup of containers"""
        for container in obj.containers.all():
            container.delete()
        super().delete_model(request, obj)
        self.message_user(request, f"Deployment {obj.pk} and its containers successfully deleted.")

    def delete_queryset(self, request, queryset):
        """Override delete_queryset to ensure proper cleanup for bulk deletions"""
        for obj in queryset:
            for container in obj.containers.all():
                container.delete()
        super().delete_queryset(request, queryset)
        self.message_user(request, f"Successfully deleted {queryset.count()} deployments and their containers.")

    def deployment_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Start</a>&nbsp;'
            '<a class="button" href="{}">Stop</a>&nbsp;'
            '<a class="button" href="{}">Sync</a>',
            f"/admin/challenges/challengedeployment/{obj.pk}/start/",
            f"/admin/challenges/challengedeployment/{obj.pk}/stop/",
            f"/admin/challenges/challengedeployment/{obj.pk}/sync/",
        )

    deployment_actions.short_description = "Actions"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:deployment_id>/start/",
                self.admin_site.admin_view(self.start_deployment_view),
                name="challengedeployment-start",
            ),
            path(
                "<int:deployment_id>/stop/",
                self.admin_site.admin_view(self.stop_deployment_view),
                name="challengedeployment-stop",
            ),
            path(
                "<int:deployment_id>/sync/",
                self.admin_site.admin_view(self.sync_deployment_view),
                name="challengedeployment-sync",
            ),
            path(
                "start_all/",
                self.admin_site.admin_view(self.start_all_view),
                name="challengedeployment-start-all",
            ),
            path(
                "stop_all/",
                self.admin_site.admin_view(self.stop_all_view),
                name="challengedeployment-stop-all",
            ),
            path(
                "sync_all/",
                self.admin_site.admin_view(self.sync_all_view),
                name="challengedeployment-sync-all",
            ),
        ]
        return custom_urls + urls

    def start_deployment_view(self, request, deployment_id):
        deployment = self.model.objects.get(pk=deployment_id)
        if deployment.start_containers():
            self.message_user(request, f"Deployment {deployment.pk} containers started successfully.")
        else:
            self.message_user(request, f"Failed to start containers for deployment {deployment.pk}.", level="ERROR")
        return handle_action_redirect(request, deployment_id)

    def stop_deployment_view(self, request, deployment_id):
        deployment = self.model.objects.get(pk=deployment_id)
        if deployment.stop_containers():
            self.message_user(request, f"Deployment {deployment.pk} containers stopped successfully.")
        else:
            self.message_user(request, f"Failed to stop containers for deployment {deployment.pk}.", level="ERROR")
        return handle_action_redirect(request, deployment_id)

    def sync_deployment_view(self, request, deployment_id):
        deployment = self.model.objects.get(pk=deployment_id)
        if deployment.sync_container_status():
            self.message_user(request, f"Deployment {deployment.pk} container status synced successfully.")
        else:
            self.message_user(request, f"Failed to sync container status for deployment {deployment.pk}.",
                              level="ERROR")
        return handle_action_redirect(request, deployment_id)

    def start_all_view(self, request):
        started = 0
        failed = 0
        for deployment in self.model.objects.all():
            if deployment.start_containers():
                started += 1
            else:
                failed += 1

        if failed:
            self.message_user(request,
                              f"Started containers for {started} deployments. Failed to start containers for {failed} deployments.",
                              level="WARNING")
        else:
            self.message_user(request, f"Successfully started containers for {started} deployments.")
        return redirect("admin:challenges_challengedeployment_changelist")

    def stop_all_view(self, request):
        stopped = 0
        failed = 0
        for deployment in self.model.objects.all():
            if deployment.stop_containers():
                stopped += 1
            else:
                failed += 1

        if failed:
            self.message_user(request,
                              f"Stopped containers for {stopped} deployments. Failed to stop containers for {failed} deployments.",
                              level="WARNING")
        else:
            self.message_user(request, f"Successfully stopped containers for {stopped} deployments.")
        return redirect("admin:challenges_challengedeployment_changelist")

    def sync_all_view(self, request):
        synced = 0
        failed = 0
        for deployment in self.model.objects.all():
            if deployment.sync_container_status():
                synced += 1
            else:
                failed += 1

        if failed:
            self.message_user(request,
                              f"Synced containers for {synced} deployments. Failed to sync containers for {failed} deployments.",
                              level="WARNING")
        else:
            self.message_user(request, f"Successfully synced containers for {synced} deployments.")
        return redirect("admin:challenges_challengedeployment_changelist")

    def start_containers(self, request, queryset):
        started = 0
        failed = 0
        for deployment in queryset:
            if deployment.start_containers():
                started += 1
            else:
                failed += 1
        if failed:
            self.message_user(request,
                              f"Started containers for {started} deployments. Failed to start containers for {failed} deployments.",
                              level="WARNING")
        else:
            self.message_user(request, f"Successfully started containers for {started} deployments.")

    def stop_containers(self, request, queryset):
        stopped = 0
        failed = 0
        for deployment in queryset:
            if deployment.stop_containers():
                stopped += 1
            else:
                failed += 1
        if failed:
            self.message_user(request,
                              f"Stopped containers for {stopped} deployments. Failed to stop containers for {failed} deployments.",
                              level="WARNING")
        else:
            self.message_user(request, f"Successfully stopped containers for {stopped} deployments.")

    def sync_container_status(self, request, queryset):
        synced = 0
        failed = 0
        for deployment in queryset:
            if deployment.sync_container_status():
                synced += 1
            else:
                failed += 1
        if failed:
            self.message_user(request,
                              f"Synced containers for {synced} deployments. Failed to sync containers for {failed} deployments.",
                              level="WARNING")
        else:
            self.message_user(request, f"Successfully synced containers for {synced} deployments.")

    start_containers.short_description = "Start containers for selected deployments"
    stop_containers.short_description = "Stop containers for selected deployments"
    sync_container_status.short_description = "Sync container status for selected deployments"


@admin.register(ChallengeNetworkConfig)
class ChallengeNetworkConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'subnet', 'template', 'deployment_id', 'containers_count')
    list_filter = ('template',)
    search_fields = ('name', 'subnet')
    readonly_fields = ('subnet',)
    actions = ['clean_network']
    change_list_template = "admin/challengenetworkconfig/change_list.html"

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
        return redirect("admin:challenges_challengenetworkconfig_changelist")

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
