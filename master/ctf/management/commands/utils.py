from datetime import timedelta, timezone
import os
import uuid

from ctf.models.enums import GameSessionStatus, TeamRole
from ctf.models.game_session import GameSession
from ctf.models.team import Team
from ctf.models.user import User


@staticmethod
def validate_environment() -> None:
    if not os.getenv("TEST_BLUE_SSH_PUBLIC_KEY") or not os.getenv("TEST_RED_SSH_PUBLIC_KEY"):
        raise ValueError("TEST_BLUE_SSH_PUBLIC_KEY or TEST_RED_SSH_PUBLIC_KEY environment variable is not set")

@staticmethod
def create_teams(run_id: uuid.UUID) -> tuple[Team, Team]:
    blue_team = Team.objects.create(name=f"Blue Team {run_id}", role=TeamRole.BLUE)
    red_team = Team.objects.create(name=f"Red Team {run_id}", role=TeamRole.RED)
    return blue_team, red_team

@staticmethod
def create_users(run_id: uuid.UUID, blue_team: Team, red_team: Team) -> None:
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

@staticmethod
def create_session() -> GameSession:
    return GameSession.objects.create(
        start_date=timezone.now(),
        end_date=timezone.now() + timedelta(days=1),
        rotation_period=1,
        status=GameSessionStatus.ACTIVE,
    )