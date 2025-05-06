from django.db import models


class GameSessionStatus(models.TextChoices):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"


class GamePhaseStatus(models.TextChoices):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
