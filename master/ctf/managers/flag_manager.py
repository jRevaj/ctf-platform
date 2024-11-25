import logging
import secrets
import string

from django.db import models

from ctf.models import GameContainer

logger = logging.getLogger(__name__)


class FlagManager(models.Manager):
    def generate_flag(self, prefix="FLAG"):
        """Generate a new random flag"""
        charset = string.ascii_letters + string.digits
        random_part = "".join(secrets.choice(charset) for _ in range(32))
        return f"{prefix}{{{random_part}}}"

    def create_flag(self, container, points, docker_service=None):
        """Create a flag for a container"""
        try:
            if not docker_service:
                raise ValueError("Docker service is required")

            if not isinstance(container, GameContainer):
                logger.error("Invalid container type")
                return None

            flag_value = self.generate_flag()
            logger.debug(f"Generated flag value: {flag_value}")

            # Create flag in database first
            flag = self.create(container=container, value=flag_value, points=points)
            logger.debug(f"Created flag: {flag}")

            if docker_service:
                docker_container = docker_service.get_container(container.docker_id)
                if not docker_container:
                    logger.error("Could not find Docker container")
                    flag.delete()
                    return None

                # Try to create directory first
                mkdir_exec = docker_container.exec_run(
                    ["mkdir", "-p", "/flags"],
                    user="ctf-user"
                )

                # Write flag as ctf-user
                container_exec = docker_container.exec_run(
                    ["sh", "-c", f'echo "{flag_value}" > /flags/flag.txt'],
                    user="ctf-user"
                )

                if container_exec.exit_code != 0:
                    logger.error(f"Failed to write flag to container: {container_exec.output}")
                    flag.delete()
                    return None

                # Set permissions after writing
                chmod_exec = docker_container.exec_run(
                    ["chmod", "644", "/flags/flag.txt"],
                    user="ctf-user"
                )

            return flag
        except Exception as e:
            logger.error(f"Error creating flag: {e}")
            return None

    def get_flag_by_value(self, value):
        """Get flag by value"""
        try:
            return self.get(value=value, is_captured=False)
        except self.model.DoesNotExist:
            return None
