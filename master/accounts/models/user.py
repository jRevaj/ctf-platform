from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.exceptions import ValidationError
from django.db import models


def validate_ssh_key(value: str) -> None:
    """Validate SSH public key format"""
    if not value.startswith(("ssh-rsa", "ssh-ed25519", "ssh-dss", "ecdsa-sha2-nistp")):
        raise ValidationError("Invalid SSH public key format")


class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=128, unique=True)
    email = models.EmailField(unique=True)
    team = models.ForeignKey("accounts.Team", related_name="users", on_delete=models.SET_NULL, null=True, blank=True)
    ssh_public_key = models.TextField(default="", blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['team']),
        ]
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.username

    def get_dirty_fields(self):
        """Get fields that have changed since the last save"""
        if not self.pk:
            return {}
        dirty_fields = {}
        for field in self._meta.fields:
            if field.name == 'id':
                continue
            original_value = getattr(self, f'_original_{field.name}', None)
            current_value = getattr(self, field.name)
            if original_value != current_value:
                dirty_fields[field.name] = current_value
        return dirty_fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self._meta.fields:
            if field.name == 'id':
                continue
            setattr(self, f'_original_{field.name}', getattr(self, field.name))

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.team and 'ssh_public_key' in self.get_dirty_fields():
            self.team.clean()
            self.team.save()
        for field in self._meta.fields:
            if field.name == 'id':
                continue
            setattr(self, f'_original_{field.name}', getattr(self, field.name))
