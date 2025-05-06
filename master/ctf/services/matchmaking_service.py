import logging
import random
from datetime import timedelta
from typing import List, Tuple

from django.utils import timezone

from accounts.models import Team
from accounts.models.enums import TeamRole
from challenges.services import ContainerService, ChallengeService
from ctf.models import GameSession, TeamAssignment, GamePhase
from ctf.models.enums import GameSessionStatus
from ctf.models.settings import GlobalSettings

logger = logging.getLogger(__name__)


class MatchmakingService:
    """Service for handling team matchmaking and container assignments"""

    def __init__(self, container_service: ContainerService = None, challenge_service: ChallengeService = None):
        self.container_service = container_service or ContainerService()
        self.challenge_service = challenge_service or ChallengeService(container_service=self.container_service)

    def create_round_assignments(self, session: GameSession, teams: list[Team]) -> bool:
        """
        Create assignments for a round using the challenge preparation system
        """
        try:
            if not teams:
                logger.warning("No teams provided for round assignments")
                return False

            logger.info(f"Creating round assignments for {len(teams)} teams")

            current_phase = session.phases.filter(status=session.status).first()
            if not current_phase:
                logger.error("No active phase found for session")
                return False

            start_date = current_phase.start_date
            end_date = current_phase.end_date

            logger.info("Preparing containers for each team")
            for team in teams:
                try:
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
                    logger.info(f"Created assignment for team {team.name}")
                except Exception as e:
                    logger.error(f"Error creating assignment for team {team.name}: {e}")
                    continue

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
            start_date = phase.start_date
            end_date = phase.end_date

            blue_assignments = TeamAssignment.objects.filter(
                session=session,
                role=TeamRole.BLUE,
                start_date__gte=phase.start_date - timedelta(days=session.rotation_period)
            ).select_related('deployment', 'team')

            team_assignments = {
                assignment.team: assignment
                for assignment in blue_assignments
            }

            teams_to_assign = list(teams)
            random.shuffle(teams_to_assign)
            available_targets = list(teams)
            for attacking_team in teams_to_assign:
                valid_targets = [t for t in available_targets if t != attacking_team]

                if not valid_targets:
                    raise Exception(f"No valid targets found for team {attacking_team.name}")

                non_recent_targets = [target for target in valid_targets if
                                      not self._attacked_target_recently(session, attacking_team, target)]
                logger.debug(f"Non-recent targets: {non_recent_targets}")

                if non_recent_targets:
                    target_team = random.choice(non_recent_targets)
                else:
                    target_team = random.choice(valid_targets)

                available_targets.remove(target_team)
                target_assignment = team_assignments.get(target_team)
                if not target_assignment:
                    raise Exception(f"No week 1 assignment found for target team {target_team.name}")

                logger.info(f"Assigning team {attacking_team.name} to attack {target_team.name}'s deployment")
                assignment = self._assign_team(session, target_assignment.deployment, attacking_team, start_date,
                                               end_date)
                if not assignment:
                    raise Exception(f"Failed to assign team {attacking_team.name} to team {target_team.name}")

                logger.info(f"Successfully created random assignment: {attacking_team.name} -> {target_team.name}")

            return True
        except Exception as e:
            logger.error(f"Error creating random red assignments: {e}")
            return False

    def create_swiss_assignments(self, session: GameSession, phase: GamePhase, teams: List[Team],
                                 number_of_tiers: int) -> bool:
        """
        Create red team assignments based on Swiss system (divide into tiers and then randomly assign within them).
        Teams will attack containers that their opponents secured in week 1
        """
        try:
            logger.info("Creating swiss system assignments")
            logger.info("Sorting teams by score")
            sorted_teams = sorted(teams, key=lambda t: t.score, reverse=True)
            if len(sorted_teams) < number_of_tiers * 2:
                logger.warning("Not enough teams for Swiss system assignments! Running random assignments instead.")
                return self.create_random_red_assignments(session, phase, teams)

            tiers = self._create_tiers(sorted_teams, number_of_tiers)
            logger.info(f"Created {len(tiers)} tiers with sizes: {[len(tier) for tier in tiers]}")
            logger.info("Tier score ranges:")
            for i, tier in enumerate(tiers):
                if tier:
                    logger.info(f"Tier {i + 1}: {tier[0].score} - {tier[-1].score}")

            assignments: list[tuple[Team, Team]] = []
            for tier in tiers:
                assignments.extend(self._create_tier_assignments(session, tier))

            blue_assignments = TeamAssignment.objects.filter(
                session=session,
                role=TeamRole.BLUE,
                start_date__gte=phase.start_date - timedelta(days=session.rotation_period)
            ).select_related('deployment', 'team')

            team_assignments = {
                assignment.team: assignment
                for assignment in blue_assignments
            }

            logger.info(f"Persisting following assignments from tiers: {assignments}")
            start_date = timezone.now()
            end_date = start_date + timedelta(days=session.rotation_period)
            for attacking_team, target_team in assignments:
                target_assignment = team_assignments.get(target_team)
                if not target_assignment:
                    raise Exception(f"No week 1 assignment found for target team {target_team.name}")

                assignment = self._assign_team(session, target_assignment.deployment, attacking_team, start_date,
                                               end_date)
                if not assignment:
                    raise Exception(f"Failed to assign team {attacking_team.name} to team {target_team.name}")

                logger.info(
                    f"Successfully created assignment: {attacking_team.name} -> {target_team.name}")

            return True
        except Exception as e:
            logger.error(f"Error creating Swiss system assignments: {e}")
            return False

    @staticmethod
    def _create_tiers(sorted_teams: list[Team], number_of_tiers: int) -> list[list[Team]]:
        """Create tiers from teams sorted by score"""
        logger.info("Creating tiers")
        base_size = len(sorted_teams) // number_of_tiers
        remainder = len(sorted_teams) % number_of_tiers

        tiers = []
        start_idx = 0
        for i in range(number_of_tiers):
            tier = sorted_teams[start_idx:start_idx + base_size]
            if tier:
                tiers.append(tier)
            start_idx += base_size

        if remainder > 0:
            remaining_teams = sorted_teams[start_idx:]
            for team in remaining_teams:
                tier_boundaries = []
                for tier in tiers:
                    if tier:
                        tier_boundaries.append({
                            'min': tier[-1].score,
                            'max': tier[0].score,
                            'tier_idx': len(tier_boundaries)
                        })

                team_score = team.score
                best_tier_idx = 0
                min_distance = float('inf')

                for boundary in tier_boundaries:
                    distance_to_min = abs(team_score - boundary['min'])
                    distance_to_max = abs(team_score - boundary['max'])
                    avg_distance = (distance_to_min + distance_to_max) / 2

                    if avg_distance < min_distance:
                        min_distance = avg_distance
                        best_tier_idx = boundary['tier_idx']

                tiers[best_tier_idx].append(team)
                tiers[best_tier_idx].sort(key=lambda t: t.score, reverse=True)
                logger.info(f"Assigned team {team.name} (score: {team_score}) to tier {best_tier_idx + 1}")

        return tiers

    def _create_tier_assignments(self, session: GameSession, teams: List[Team]) -> List[Tuple[Team, Team]]:
        """
        Create assignments for teams within the same tier
        """
        logger.info("Creating tier assignments")
        assignments = []

        if len(teams) < 2:
            return assignments

        teams_to_assign = list(teams)
        random.shuffle(teams_to_assign)
        available_targets = list(teams)
        for attacking_team in teams_to_assign:
            valid_targets = [t for t in available_targets if t != attacking_team]

            if not valid_targets:
                logger.warning(f"No valid targets found for team {attacking_team.name} in tier")
                continue

            non_recent_targets = [target for target in valid_targets if
                                  not self._attacked_target_recently(session, attacking_team, target)]

            if non_recent_targets:
                target_team = random.choice(non_recent_targets)
            else:
                target_team = random.choice(valid_targets)

            logger.debug(f"Found target team for {attacking_team}: {target_team.name}")
            available_targets.remove(target_team)
            assignments.append((attacking_team, target_team))

        return assignments

    def _assign_team(self, session, target_deployment, red_team, start_date, end_date) -> TeamAssignment:
        """
        Assign a red team to a target deployment
        """
        for container in target_deployment.containers.all():
            if not container.is_running():
                logger.warning(f"Container {container.name} is not running, starting it...")
                self.container_service.start_container(container)
                if not container.is_running():
                    logger.error(f"Failed to start container {container.name}")
                    continue

            if container.is_entrypoint:
                logger.info(f"Swapping SSH access for {red_team.name} to {container.name}")
                self.container_service.swap_ssh_access(container, red_team)
            container.red_team = red_team
            container.save()

        return TeamAssignment.objects.create(
            session=session,
            team=red_team,
            deployment=target_deployment,
            role=TeamRole.RED,
            start_date=start_date,
            end_date=end_date
        )

    @staticmethod
    def _attacked_target_recently(session: GameSession, attacker: Team, target: Team) -> bool:
        """
        Check if team attacked selected target in previous game sessions.
        This ensures teams don't repeatedly attack the same opponents.
        The number of previous sessions to check is configurable in global settings.
        """
        settings = GlobalSettings.get_settings()
        check_count = settings.previous_targets_check_count

        previous_sessions = GameSession.objects.filter(
            start_date__lt=session.start_date,
            status=GameSessionStatus.COMPLETED
        ).order_by('-start_date')[:check_count]

        if not previous_sessions:
            return False

        for previous_session in previous_sessions:
            blue_assignment = previous_session.team_assignments.get(
                team=target,
                role=TeamRole.BLUE
            )

            if not blue_assignment:
                continue

            previous_target_deployment = blue_assignment.deployment

            if TeamAssignment.objects.filter(
                    session=previous_session,
                    team=attacker,
                    role=TeamRole.RED,
                    deployment=previous_target_deployment
            ).exists():
                return True

        return False
