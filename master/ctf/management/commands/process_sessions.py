import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from ctf.models import GameSession
from ctf.models.enums import GameSessionStatus
from ctf.services.matchmaking_service import MatchmakingService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Process planned game sessions that are ready to start"

    def handle(self, *args, **options):
        try:
            now = timezone.now()
            planned_sessions = GameSession.objects.filter(
                status=GameSessionStatus.PLANNED,
                start_date__lte=now
            )

            if not planned_sessions.exists():
                logger.info("No planned sessions ready to start")
                return

            matchmaking_service = MatchmakingService()
            
            for session in planned_sessions:
                logger.info(f"Processing planned session: {session.name}")
                
                try:
                    # Update session status
                    session.status = GameSessionStatus.ACTIVE
                    session.save(update_fields=['status'])
                    
                    # Create first round assignments
                    teams = session.get_teams()
                    if not teams:
                        logger.warning(f"No teams found for session {session.name}")
                        continue
                        
                    success = matchmaking_service.create_round_assignments(session, teams)
                    if success:
                        logger.info(f"Successfully prepared first round for session {session.name}")
                    else:
                        logger.error(f"Failed to prepare first round for session {session.name}")
                        
                except Exception as e:
                    logger.error(f"Error processing session {session.name}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error processing planned sessions: {e}")
            raise 