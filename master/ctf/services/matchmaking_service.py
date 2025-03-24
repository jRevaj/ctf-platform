import logging
import random
from datetime import timedelta
from typing import List, Tuple

from django.db.models import Q
from django.utils import timezone

from ctf.models import Team, GameSession, TeamAssignment, GamePhase
from ctf.models.enums import TeamRole
from ctf.services.challenge_service import ChallengeService
from ctf.services.container_service import ContainerService

logger = logging.getLogger(__name__)


class MatchmakingService:
    """Service for handling team matchmaking and container assignments"""

    def __init__(self, container_service: ContainerService = None, challenge_service: ChallengeService = None):
        self.container_service = container_service or ContainerService()
        self.challenge_service = challenge_service or ChallengeService(container_service=self.container_service)

    def create_round_assignments(self, session: GameSession, teams: List[Team]) -> bool:
        """
        Create assignments for a round using the challenge preparation system
        """
        try:
            logger.info("Creating round assignments")
            template = session.template
            start_date = timezone.now()
            end_date = start_date + timedelta(days=session.rotation_period)

            logger.info("Preparing containers for each team")
            for team in teams:
                containers = self.challenge_service.prepare_challenge(template, team)
                if not containers:
                    logger.error(f"Failed to prepare challenge for team {team.name}")
                    continue

                for container in containers:
                    TeamAssignment.objects.create(
                        session=session,
                        team=team,
                        container=container,
                        role=TeamRole.BLUE,
                        start_date=start_date,
                        end_date=end_date
                    )

            return True
        except Exception as e:
            logger.error(f"Error creating round assignments: {e}")
            return False

    @staticmethod
    def create_random_red_assignments(session: GameSession, teams: List[Team], phase: GamePhase) -> bool:
        """
        Create random red team assignments for the second week
        Teams will attack containers that their opponents secured in week 1
        """
        try:
            logger.info("Creating random red team assignments")
            start_date = phase.start_date + timedelta(days=session.rotation_period)
            end_date = start_date + timedelta(days=session.rotation_period)

            logger.info("Getting containers secured by teams in week 1")
            blue_assignments = TeamAssignment.objects.filter(
                session=session,
                role=TeamRole.BLUE,
                start_date__gte=phase.start_date
            ).select_related('container', 'team')

            logger.info("Shuffling teams")
            shuffled_teams = list(teams)
            random.shuffle(shuffled_teams)

            logger.info("Assigning teams to containers")
            for team in shuffled_teams:
                available_containers = [
                    assignment for assignment in blue_assignments
                    if assignment.team != team
                ]

                if not available_containers:
                    logger.error(f"No available containers for team {team.name}")
                    continue

                target_assignment = random.choice(available_containers)

                TeamAssignment.objects.create(
                    session=session,
                    team=team,
                    container=target_assignment.container,
                    role=TeamRole.RED,
                    start_date=start_date,
                    end_date=end_date
                )

            return True
        except Exception as e:
            logger.error(f"Error creating random red assignments: {e}")
            return False

    def create_swiss_assignments(self, session: GameSession, teams: List[Team]) -> bool:
        """
        Create red team assignments based on Swiss system pairing
        Teams will attack containers that their opponents secured in week 1
        """
        try:
            logger.info("Creating swiss system assignments")
            logger.info("Sorting teams by score")
            sorted_teams = sorted(teams, key=lambda t: t.score, reverse=True)
            total_teams = len(sorted_teams)

            logger.info("Dividing teams into thirds")
            third_size = total_teams // 3
            top_third = sorted_teams[:third_size]
            middle_third = sorted_teams[third_size:2 * third_size]
            bottom_third = sorted_teams[2 * third_size:]

            assignments = []

            logger.info("Matching teams within their respective tiers")
            assignments.extend(self._create_tier_assignments(session, top_third))
            assignments.extend(self._create_tier_assignments(session, middle_third))
            assignments.extend(self._create_tier_assignments(session, bottom_third))

            logger.info("Handling any remaining teams (if total teams not divisible by 3)")
            remaining_teams = sorted_teams[3 * third_size:]
            if remaining_teams:
                assignments.extend(self._create_tier_assignments(session, remaining_teams))

            logger.info("Persisting red team assignments to db")
            start_date = timezone.now()
            end_date = start_date + timedelta(days=session.rotation_period)

            for blue_team, red_team in assignments:
                blue_containers = TeamAssignment.objects.filter(
                    session=session,
                    team=blue_team,
                    role=TeamRole.BLUE,
                    start_date__gte=start_date - timedelta(days=session.rotation_period)
                ).select_related('container')

                for blue_assignment in blue_containers:
                    TeamAssignment.objects.create(
                        session=session,
                        team=red_team,
                        container=blue_assignment.container,
                        role=TeamRole.RED,
                        start_date=start_date,
                        end_date=end_date
                    )

            return True
        except Exception as e:
            logger.error(f"Error creating Swiss system assignments: {e}")
            return False

    def _create_tier_assignments(self, session: GameSession, teams: List[Team]) -> List[Tuple[Team, Team]]:
        """
        Create assignments for teams within the same tier
        """
        logger.info("Creating tier assignments")
        assignments = []
        teams_copy = teams.copy()

        while len(teams_copy) >= 2:
            team1 = teams_copy.pop(0)

            opponent = None
            for team2 in teams_copy:
                if not self._have_teams_met_recently(session, team1, team2):
                    opponent = team2
                    teams_copy.remove(team2)
                    break

            if not opponent and teams_copy:
                opponent = teams_copy.pop(0)

            if opponent:
                assignments.append((team1, opponent))

        return assignments

    @staticmethod
    def _have_teams_met_recently(session: GameSession, team1: Team, team2: Team, lookback_days: int = 14) -> bool:
        """
        Check if two teams have faced each other recently
        """
        cutoff_date = timezone.now() - timedelta(days=lookback_days)

        recent_match1 = TeamAssignment.objects.filter(
            Q(session=session) &
            Q(team=team1) &
            Q(role=TeamRole.RED) &
            Q(container__blue_team=team2) &
            Q(start_date__gte=cutoff_date)
        ).exists()

        recent_match2 = TeamAssignment.objects.filter(
            Q(session=session) &
            Q(team=team2) &
            Q(role=TeamRole.RED) &
            Q(container__blue_team=team1) &
            Q(start_date__gte=cutoff_date)
        ).exists()

        return recent_match1 or recent_match2
