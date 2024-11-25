from django.db import models


class TeamRole(models.TextChoices):
    BLUE = "Blue"
    RED = "Red"


class ContainerStatus(models.TextChoices):
    CREATED = "Created"
    RUNNING = "Running"
    STOPPED = "Stopped"
    DELETED = "Deleted"
    ERROR = "Error"


class GameSessionStatus(models.TextChoices):
    PLANNED = "Planned"
    ACTIVE = "Active"
    COMPLETED = "Completed"
