import logging

from celery import shared_task
from django.utils import timezone

from ctf.models import GameSession, Team, GamePhase
from ctf.models.enums import GameSessionStatus, TeamRole
from ctf.models.settings import GlobalSettings
from ctf.services.matchmaking_service import MatchmakingService
from ctf.utils import is_first_session_for_teams

logger = logging.getLogger(__name__)


@shared_task
def process_sessions():
    logger.info("Running process_sessions task")
    try:
        planned_sessions = GameSession.objects.filter(
            status=GameSessionStatus.PLANNED,
            start_date__lte=timezone.now(),
        )

        if not planned_sessions.exists():
            logger.info("No planned sessions ready to start")
            return

        matchmaking_service = MatchmakingService()

        for session in planned_sessions:
            logger.info(f"Processing planned session: {session.name}")
            try:
                teams = list(Team.objects.filter(is_in_game=True))
                if not teams:
                    logger.warning(f"No teams found for session {session.name}")
                    continue

                success = matchmaking_service.create_round_assignments(session, teams)
                if success:
                    session.status = GameSessionStatus.ACTIVE
                    phase = session.phases.filter(phase_name=TeamRole.BLUE).first()
                    phase.status = GameSessionStatus.ACTIVE
                    phase.save(update_fields=["status"])
                    session.save(update_fields=['status'])
                    logger.info(f"Successfully prepared first round for session {session.name}")
                else:
                    logger.error(f"Failed to prepare first round for session {session.name}")
            except Exception as e:
                logger.error(f"Error processing session {session.name}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error processing planned sessions: {e}")
        raise


@shared_task
def process_phases():
    logger.info("Running process_phases task")
    try:
        active_sessions = GameSession.objects.filter(
            status=GameSessionStatus.ACTIVE
        ).prefetch_related('phases')

        if not active_sessions.exists():
            logger.info("No active sessions found for phase rotation")
            return

        matchmaking_service = MatchmakingService()

        for session in active_sessions:
            blue_phase = session.phases.filter(
                status=GameSessionStatus.ACTIVE,
                phase_name=TeamRole.BLUE,
                end_date__lte=timezone.now(),
            ).first()

            if not blue_phase:
                logger.info(f"No overdue blue phase found for session: {session.name}")
                continue

            logger.info(f"Processing phase transition for session: {session.name}")

            try:
                red_phase = session.phases.get(phase_name=TeamRole.RED)

                teams = list(session.get_teams())
                if not teams:
                    logger.warning(f"No teams found for session {session.name}")
                    continue

                if is_first_session_for_teams(teams):
                    logger.info(f"Using random matching for first session: {session.name}")
                    success = matchmaking_service.create_random_red_assignments(session, red_phase, teams)
                else:
                    logger.info(f"Using Swiss matching for subsequent session: {session.name}")
                    settings = GlobalSettings.get_settings()
                    success = matchmaking_service.create_swiss_assignments(session, red_phase, teams, settings.number_of_tiers)

                if success:
                    blue_phase.status = GameSessionStatus.COMPLETED
                    blue_phase.save(update_fields=["status"])
                    red_phase.status = GameSessionStatus.ACTIVE
                    red_phase.save(update_fields=["status"])
                    logger.info(f"Successfully transitioned to red phase for session {session.name}")
                else:
                    logger.error(f"Failed to transition to red phase for session {session.name}")

            except GamePhase.DoesNotExist:
                logger.error(f"Red phase not found for session {session.name}")
                continue
            except Exception as e:
                logger.error(f"Error processing transition for session {session.name}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error processing phase transitions: {e}")
        raise
