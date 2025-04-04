import logging

from django.utils import timezone

from ctf.models import Flag, Team, GameSession

logger = logging.getLogger(__name__)


class FlagService:
    @staticmethod
    def capture_and_award(flag: Flag, captured_by: Team) -> None:
        """Handle flag capture"""
        flag.capture(captured_by)
        # TODO: good idea??
        # Calculate points based on time taken
        # points = self._calculate_points(flag)
        captured_by.red_points += flag.points
        captured_by.update_score()

    @staticmethod
    def award_blue_points(flags: list[Flag]) -> None:
        """Award blue points for flags secured by the blue team"""
        if len(set(flag.owner for flag in flags)) != 1 or len(set(flag.session for flag in flags)) != 1:
            raise ValueError("Flags must belong to the same team and session")
        
        owner = flags[0].owner
        total_points = sum(flag.points for flag in flags)
        owner.blue_points += total_points
        owner.update_score()

    @staticmethod
    def calculate_points(flag: Flag) -> int:
        """Calculate points based on time since flag creation"""
        # TODO: decide if we want this
        base_points = flag.points
        time_factor = 1.0

        hours_since_creation = (timezone.now() - flag.created_at).total_seconds() / 3600
        if hours_since_creation > 24:
            time_factor = max(0.5, 1 - (hours_since_creation - 24) / 48)

        return int(base_points * time_factor)
