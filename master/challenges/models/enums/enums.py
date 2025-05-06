from django.db import models


class ContainerStatus(models.TextChoices):
    CREATED = "created"
    RUNNING = "running"
    STOPPED = "stopped"
    DELETED = "deleted"
    ERROR = "error"
