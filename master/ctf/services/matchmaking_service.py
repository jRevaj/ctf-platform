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
            start_date = timezone.now()
            end_date = start_date + timedelta(days=session.rotation_period)

            logger.info("Preparing containers for each team")
            for team in teams:
                deployment = self.challenge_service.prepare_challenge(session, team)
                if not deployment:
                    logger.error(f"Failed to prepare challenge for team {team.name}")
                    continue

                TeamAssignment.objects.create(
                    session=session,
                    team=team,
                    deployment=deployment,
                    role=TeamRole.BLUE,
                    start_date=start_date,
                    end_date=end_date
                )

            return True
        except Exception as e:
            logger.error(f"Error creating round assignments: {e}")
            return False

    def create_random_red_assignments(self, session: GameSession, phase: GamePhase, teams: List[Team]) -> bool:
        """
        Create random red team assignments for the second week.
        Each team will be randomly assigned to attack another team's setup from week 1.
        Teams cannot be assigned to their own setup.
        """
        try:
            logger.info("Creating random red team assignments")
            start_date = phase.start_date + timedelta(days=session.rotation_period)
            end_date = start_date + timedelta(days=session.rotation_period)

            blue_assignments = TeamAssignment.objects.filter(
                session=session,
                role=TeamRole.BLUE,
                start_date__gte=phase.start_date
            ).select_related('deployment', 'team')

            team_assignments = {
                assignment.team: assignment 
                for assignment in blue_assignments
            }

            teams_to_assign = list(teams)
            random.shuffle(teams_to_assign)

            available_targets = list(teams)
            random.shuffle(available_targets)

            for attacking_team in teams_to_assign:
                valid_targets = [t for t in available_targets if t != attacking_team]
                
                if not valid_targets:
                    logger.error(f"No valid targets found for team {attacking_team.name}")
                    raise Exception(f"No valid targets found for team {attacking_team.name}")

                target_team = random.choice(valid_targets)
                available_targets.remove(target_team)

                target_assignment = team_assignments.get(target_team)
                if not target_assignment:
                    logger.error(f"No week 1 assignment found for target team {target_team.name}")
                    raise Exception(f"No week 1 assignment found for target team {target_team.name}")

                logger.info(f"Assigning team {attacking_team.name} to attack {target_team.name}'s deployment")
                entry_container = target_assignment.deployment.containers.filter(is_entrypoint=True).first()

                if not entry_container:
                    logger.error(f"No entrypoint container found for {target_team.name}'s deployment")
                    raise Exception(f"No entrypoint container found for {target_team.name}'s deployment")

                logger.info(f"Swapping SSH access for {attacking_team.name} to {entry_container.name}")
                self.container_service.swap_ssh_access(entry_container, attacking_team)

                TeamAssignment.objects.create(
                    session=session,
                    team=attacking_team,
                    deployment=target_assignment.deployment,
                    role=TeamRole.RED,
                    start_date=start_date,
                    end_date=end_date
                )
                logger.info(f"Successfully created random assignment: {attacking_team.name} -> {target_team.name}")

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
                ).select_related('deployment')

                for blue_assignment in blue_containers:
                    TeamAssignment.objects.create(
                        session=session,
                        team=red_team,
                        deployment=blue_assignment.deployment,
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
