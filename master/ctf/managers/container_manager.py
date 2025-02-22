import logging
import os
from django.conf import settings
from django.db import models

from ctf.models.enums import ContainerStatus
from ctf.models.constants import DockerConstants
from ctf.models.exceptions import ContainerOperationError

logger = logging.getLogger(__name__)


class GameContainerManager(models.Manager):
    """Custom manager for GameContainer model"""

    def create_with_docker(self, template, session, blue_team, red_team, docker_service):
        """Create a new game container with Docker container"""
        try:
            container_name = f"{DockerConstants.CONTAINER_PREFIX}{session.pk}-{blue_team.pk}-{red_team.pk}"
            image_tag = f"ctf-{template.folder}:{session.pk}"
            build_path = os.path.join(settings.BASE_DIR, f"container-templates/{template.folder}")

            docker_service.build_image(build_path, image_tag)
            docker_container = docker_service.create_container(image_tag, container_name)

            return self.create(
                name=container_name,
                docker_id=docker_container.id,
                status=ContainerStatus.RUNNING,
                template=template,
                current_blue_team=blue_team,
                current_red_team=red_team,
                access_rotation_date=session.end_date,
            )
        except Exception as e:
            logger.error(f"Failed to create game container: {e}")
            raise ContainerOperationError(f"Failed to create container: {e}")

    def get_by_docker_id(self, docker_id):
        """Get container by Docker ID"""
        return self.get(docker_id=docker_id)
    
    def get_by_template(self, template):
        """Get container by template"""
        return self.filter(template=template)

    def get_by_ip_address(self, ip_address):
        """Get container by IP address"""
        return self.get(ip_address=ip_address)

    def get_active(self):
        """Get all active containers"""
        return self.filter(status='RUNNING')

    def get_for_team(self, team):
        """Get all containers accessible by a team"""
        return self.filter(
            models.Q(current_blue_team=team) | 
            models.Q(current_red_team=team)
        )
                        