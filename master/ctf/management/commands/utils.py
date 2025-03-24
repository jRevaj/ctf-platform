import os
import uuid
from datetime import timedelta

from django.utils.timezone import localtime

from ctf.models.enums import GameSessionStatus, TeamRole
from ctf.models.game_session import GameSession
from ctf.models.team import Team
from ctf.models.user import User


def validate_environment() -> None:
    if not os.getenv("TEST_BLUE_SSH_PUBLIC_KEY") or not os.getenv("TEST_RED_SSH_PUBLIC_KEY"):
        raise ValueError("TEST_BLUE_SSH_PUBLIC_KEY or TEST_RED_SSH_PUBLIC_KEY environment variable is not set")


def create_teams(run_id: uuid.UUID, count: int) -> list[Team]:
    return [Team.objects.create(name=f"Team {i} {run_id}") for i in range(count)]


def create_users(run_id: uuid.UUID, count: int) -> list[User]:
    return [User.objects.create(
        username=f"User {i} {run_id}",
        email=f"test-{i}-{run_id}@example.com",
        ssh_public_key=os.getenv("TEST_BLUE_SSH_PUBLIC_KEY"),
        is_active=True
    ) for i in range(count)]


def create_users_with_key(run_id: uuid.UUID, blue_team: Team, red_team: Team) -> None:
    User.objects.create(
        username=f"test-{run_id}",
        email=f"test-{run_id}@example.com",
        ssh_public_key=os.getenv("TEST_BLUE_SSH_PUBLIC_KEY"),
        is_active=True,
        team=blue_team,
    )
    User.objects.create(
        username=f"testing-{run_id}",
        email=f"testing-{run_id}@example.com",
        ssh_public_key=os.getenv("TEST_RED_SSH_PUBLIC_KEY"),
        is_active=True,
        team=red_team,
    )


def create_session() -> GameSession:
    return GameSession.objects.create(
        start_date=localtime(),
        end_date=localtime() + timedelta(days=1),
        rotation_period=1,
        status=GameSessionStatus.ACTIVE,
    )
