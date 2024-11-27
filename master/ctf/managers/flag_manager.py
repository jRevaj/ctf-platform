import logging
import secrets
import string

from django.db import models

logger = logging.getLogger(__name__)


class FlagManager(models.Manager):
    """Custom manager for Flag model"""

    def generate_flag(self, prefix="FLAG"):
        """Generate a new random flag"""
        charset = string.ascii_letters + string.digits
        random_part = "".join(secrets.choice(charset) for _ in range(32))
        return f"{prefix}{{{random_part}}}"

    def create_flag(self, container, points):
        """Create a flag for a container"""
        try:
            flag_value = self.generate_flag()
            return self.create(container=container, value=flag_value, points=points)
        except Exception as e:
            logger.error(f"Error creating flag: {e}")
            return None

    def get_flag_by_value(self, value):
        """Get flag by value"""
        try:
            return self.get(value=value, is_captured=False)
        except self.model.DoesNotExist:
            return None
