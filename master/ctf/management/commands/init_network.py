from django.core.management.base import BaseCommand

from challenges.services import DockerService


class Command(BaseCommand):
    help = "Initialize network for deployments"

    def handle(self, *args, **options):
        try:
            print("Creating network ctf-platform_user_net")
            docker_service = DockerService()
            docker_service.client.networks.create(name="ctf-platform_user_net", driver="bridge")
        except Exception as e:
            print(f"Failed to create network ctf-platform_user_net: {e}")
