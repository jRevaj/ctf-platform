from django.db import models


class TeamRole(models.TextChoices):
    BLUE = "blue"
    RED = "red"


class ContainerStatus(models.TextChoices):
    CREATED = "created"
    RUNNING = "running"
    STOPPED = "stopped"
    DELETED = "deleted"
    ERROR = "error"


class GameSessionStatus(models.TextChoices):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"


class PhaseNumber(models.TextChoices):
    FIRST = "1", "Blue"
    SECOND = "2", "Red"
