from django.db import models


class TeamRole(models.TextChoices):
    BLUE = "blue"
    RED = "red"
