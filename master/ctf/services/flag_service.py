import logging

from accounts.models.enums import TeamRole
from ctf.models import Flag, GameSession

logger = logging.getLogger(__name__)


class FlagService:
    # TODO: think of flag checkers - provide endpoints that containers can connect to?

    @staticmethod
    def capture_and_award(flag: Flag, captured_by_user) -> None:
        """Handle flag capture"""
        captured_by = captured_by_user.team
        flag.capture(captured_by, captured_by_user)
        captured_by.red_points += flag.points
        captured_by.update_score()

    @staticmethod
    def award_blue_points(flags: list[Flag]) -> None:
        """Award blue points for flags secured by the blue team"""
        if not flags:
            return

        if len(set(flag.owner for flag in flags)) != 1:
            raise ValueError("All flags must belong to the same team")

        team = flags[0].owner
        total_points = sum(flag.points for flag in flags)
        team.blue_points += total_points
        team.update_score()
        logger.info(f"Awarded {total_points} blue points to team {team.name}")

    def distribute_uncaptured_flags_points(self, session: GameSession) -> None:
        """Distribute points for uncaptured flags to corresponding blue teams"""
        deployments = session.team_assignments.values_list('deployment', flat=True).distinct()

        uncaptured_flags = Flag.objects.filter(
            container__deployment__in=deployments,
            is_captured=False
        ).select_related('container', 'container__deployment')

        flags_by_team = {}
        for flag in uncaptured_flags:
            blue_assignment = session.team_assignments.filter(
                deployment=flag.container.deployment,
                role=TeamRole.BLUE
            ).first()

            if blue_assignment:
                team = blue_assignment.team
                if team not in flags_by_team:
                    flags_by_team[team] = []
                flags_by_team[team].append(flag)

        for team, flags in flags_by_team.items():
            self.award_blue_points(flags)

    # TODO: implement showing hints of unsubmitted flags + points deduction system