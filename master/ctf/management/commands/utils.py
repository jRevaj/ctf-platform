import logging
import os
import uuid
from datetime import timedelta

from django.utils.timezone import localtime

from ctf.models import ChallengeTemplate
from ctf.models.enums import GameSessionStatus
from ctf.models.game_session import GameSession
from ctf.models.team import Team
from ctf.models.user import User

logger = logging.getLogger(__name__)


def validate_environment() -> None:
    if not os.getenv("TEST_BLUE_SSH_PUBLIC_KEY") or not os.getenv("TEST_RED_SSH_PUBLIC_KEY"):
        raise ValueError("TEST_BLUE_SSH_PUBLIC_KEY or TEST_RED_SSH_PUBLIC_KEY environment variable is not set")


def create_teams(run_id: uuid.UUID, count: int) -> list[Team]:
    return [Team.objects.create(name=f"Team {i} {run_id}") for i in range(count)]


def create_users(run_id: uuid.UUID, count: int, with_keys: bool = False) -> list[User]:
    if with_keys and count > 8:
        logger.warning('Too many users for setting up ssh keys. Using single key for all users!')
        with_keys = False

    return [User.objects.create(
        username=f"User {i} {run_id}",
        email=f"test-{i}@example.com",
        ssh_public_key=os.getenv(f"TEST_SSH_PUBLIC_KEY_{i}") if with_keys else os.getenv("TEST_BLUE_SSH_PUBLIC_KEY"),
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


def create_session(template: ChallengeTemplate, run_id: uuid.UUID) -> GameSession:
    return GameSession.objects.create(
        name=f"{template.name}-{run_id}",
        template=template,
        start_date=localtime(),
        end_date=localtime() + timedelta(days=1),
        rotation_period=1,
        status=GameSessionStatus.ACTIVE,
    )
