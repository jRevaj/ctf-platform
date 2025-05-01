import logging
import secrets
import string
from datetime import datetime, timezone

from django.db import models

logger = logging.getLogger(__name__)


def generate_flag(prefix="flag"):
    """Generate a new random flag"""
    charset = string.ascii_letters + string.digits
    random_part = "".join(secrets.choice(charset) for _ in range(32))
    return f"{prefix}{{{random_part}}}"


class FlagManager(models.Manager):
    """Custom manager for Flag model"""

    def create_flag(self, owner, points, placeholder="", hint=""):
        """Create a flag"""
        try:
            flag_value = generate_flag()
            return self.create(value=flag_value, points=points, placeholder=placeholder, hint=hint, owner=owner)
        except Exception as e:
            logger.error(f"Error creating flag: {e}")
            return None

    def get_flag_by_value(self, value):
        """Get flag by value"""
        try:
            return self.get(value=value, is_captured=False)
        except self.model.DoesNotExist:
            return None

    def get_flags_by_template(self, template):
        """Get flags by template"""
        return self.filter(container__template=template)


class Flag(models.Model):
    value = models.CharField(max_length=128, unique=True)
    points = models.IntegerField(default=100)
    placeholder = models.CharField(max_length=128, default="", blank=True)
    hint = models.TextField(default="", blank=True)
    container = models.ForeignKey(
        "ctf.GameContainer",
        related_name="flags",
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )
    owner = models.ForeignKey(
        "ctf.Team",
        related_name="owned_flags",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    is_captured = models.BooleanField(default=False)
    captured_by = models.ForeignKey(
        "ctf.Team",
        related_name="captured_flags",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    captured_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = FlagManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["value"]),
        ]
        verbose_name = "Flag"
        verbose_name_plural = "Flags"

    def __str__(self):
        return self.value

    def capture(self, team):
        """Mark the flag as captured"""
        self.is_captured = True
        self.captured_by = team
        self.captured_at = datetime.now(timezone.utc)
        self.save(update_fields=["is_captured", "captured_by", "captured_at"])

    def release(self):
        """Release the flag"""
        self.is_captured = False
        self.captured_by = None
        self.captured_at = None
        self.save(update_fields=["is_captured", "captured_by", "captured_at"])
