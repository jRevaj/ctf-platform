import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from accounts.models import Team
from accounts.models.enums import TeamRole
from ctf.models import GameSession, GamePhase
from ctf.models.enums import GameSessionStatus, GamePhaseStatus
from ctf.models.settings import GlobalSettings
from ctf.services import MatchmakingService
from ctf.utils.helpers import is_first_session_for_teams

logger = logging.getLogger(__name__)


@shared_task
def process_sessions():
    """Process planned sessions that are ready to start
    
    This task checks for sessions that are planned to start at the current time
    and creates round assignments for them.
    
    Raises:
        Exception: If there's an error processing planned sessions or if any session fails to process
    """
    logger.info("Running process_sessions task")

    planned_sessions = GameSession.objects.filter(
        status=GameSessionStatus.PLANNED,
        start_date__lte=timezone.now(),
    )
    teams = list(Team.objects.filter(is_in_game=True))

    if not planned_sessions.exists():
        logger.info("No planned sessions ready to start")
        return
    elif not teams:
        logger.info("No teams to deploy planned challenges for")
        return

    matchmaking_service = MatchmakingService()
    failed_sessions = []

    for session in planned_sessions:
        logger.info(f"Processing planned session: {session.name}")
        try:
            with transaction.atomic():
                success = matchmaking_service.create_round_assignments(session, teams)
                if success:
                    session.status = GameSessionStatus.ACTIVE
                    phase = session.phases.filter(phase_name=TeamRole.BLUE).first()
                    phase.status = GamePhaseStatus.ACTIVE
                    phase.save(update_fields=["status"])
                    session.save(update_fields=['status'])
                    logger.info(f"Successfully prepared first round for session {session.name}")
                else:
                    error_msg = f"Failed to prepare first round for session {session.name}"
                    logger.error(error_msg)
                    failed_sessions.append((session.name, error_msg))
        except Exception as e:
            error_msg = f"Error processing session {session.name}: {str(e)}"
            logger.error(error_msg)
            failed_sessions.append((session.name, error_msg))

    if failed_sessions:
        error_details = "\n".join([f"- {name}: {error}" for name, error in failed_sessions])
        raise Exception(f"Failed to process some sessions:\n{error_details}")

    logger.info("Successfully processed all planned sessions")


@shared_task
def process_phases():
    """Process phase transitions for active sessions
    
    This task checks for overdue phases and transitions to the next phase.
    It handles both the transition from blue phase to red phase and the transition from red phase to completed session.
    
    Raises:
        Exception: If there's an error processing phase transitions or if any session fails to transition
    """
    logger.info("Running process_phases task")

    active_sessions = GameSession.objects.filter(
        status=GameSessionStatus.ACTIVE
    ).prefetch_related('phases')

    if not active_sessions.exists():
        logger.info("No active sessions found for phase rotation")
        return

    matchmaking_service = MatchmakingService()
    failed_sessions = []

    for session in active_sessions:
        logger.info(f"Processing phase transition for session: {session.name}")

        try:
            red_phase = session.phases.filter(
                status=GamePhaseStatus.ACTIVE,
                phase_name=TeamRole.RED,
                end_date__lte=timezone.now(),
            ).first()

            if red_phase:
                logger.info(f"Red phase overdue for session: {session.name}, completing session")
                with transaction.atomic():
                    session.status = GameSessionStatus.COMPLETED
                    session.save(update_fields=["status"])
                continue

            blue_phase = session.phases.filter(
                status=GamePhaseStatus.ACTIVE,
                phase_name=TeamRole.BLUE,
                end_date__lte=timezone.now(),
            ).first()

            if not blue_phase:
                logger.info(f"No overdue blue phase found for session: {session.name}")
                continue

            try:
                red_phase = session.phases.get(phase_name=TeamRole.RED)
                teams = list(session.get_teams)

                if not teams:
                    error_msg = f"No teams found for session {session.name}"
                    logger.warning(error_msg)
                    failed_sessions.append((session.name, error_msg))
                    continue

                with transaction.atomic():
                    if is_first_session_for_teams(teams):
                        logger.info(f"Using random matching for first session: {session.name}")
                        success = matchmaking_service.create_random_red_assignments(session, red_phase, teams)
                    else:
                        logger.info(f"Using Swiss matching for subsequent session: {session.name}")
                        settings = GlobalSettings.get_settings()
                        success = matchmaking_service.create_swiss_assignments(
                            session, red_phase, teams, settings.number_of_tiers
                        )

                    if success:
                        blue_phase.status = GamePhaseStatus.COMPLETED
                        blue_phase.save(update_fields=["status"])
                        red_phase.status = GamePhaseStatus.ACTIVE
                        red_phase.save(update_fields=["status"])
                        logger.info(f"Successfully transitioned to red phase for session {session.name}")
                    else:
                        error_msg = f"Failed to transition to red phase for session {session.name}"
                        logger.error(error_msg)
                        failed_sessions.append((session.name, error_msg))

            except GamePhase.DoesNotExist:
                error_msg = f"Red phase not found for session {session.name}"
                logger.error(error_msg)
                failed_sessions.append((session.name, error_msg))
                continue

        except Exception as e:
            error_msg = f"Error processing transition for session {session.name}: {str(e)}"
            logger.error(error_msg)
            failed_sessions.append((session.name, error_msg))

    if failed_sessions:
        error_details = "\n".join([f"- {name}: {error}" for name, error in failed_sessions])
        raise Exception(f"Failed to process some phase transitions:\n{error_details}")

    logger.info("Successfully processed all phase transitions")
