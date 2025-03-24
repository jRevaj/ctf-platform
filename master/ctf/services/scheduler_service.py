import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from ctf.models import GameSession, GamePhase
from ctf.models.enums import PhaseNumber
from ctf.services.matchmaking_service import MatchmakingService

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing round scheduling and automatic rotations"""

    def __init__(self, matchmaking_service=None):
        self.matchmaking_service = matchmaking_service or MatchmakingService()

    @staticmethod
    def schedule_round(session: GameSession, template, start_date):
        """Schedule a new round with the given template"""
        try:
            with transaction.atomic():
                # TODO: fix rounds does not exist on session model
                current_round_number = session.rounds.count()
                next_round_number = current_round_number + 1

                if not start_date:
                    if current_round_number > 0:
                        current_round = session.rounds.latest('round_number')
                        start_date = current_round.start_date + timedelta(days=session.rotation_period * 2)
                    else:
                        start_date = timezone.now()

                phase = GamePhase.objects.create(
                    session=session,
                    template=template,
                    status='planned',
                    phase_number=next_round_number,
                    start_date=start_date,
                )

                logger.info(f"Scheduled phase {phase.get_phase_number_display()} for session {session.name}")
                return phase
        except Exception as e:
            logger.error(f"Error scheduling round: {e}")
            return None

    def process_scheduled_rounds(self):
        """Process all scheduled rounds and handle rotations"""
        try:
            active_sessions = GameSession.objects.filter(status='active')

            for session in active_sessions:
                self._process_session_rounds(session)
        except Exception as e:
            logger.error(f"Error processing scheduled rounds: {e}")

    def _process_session_rounds(self, session: GameSession):
        """Process rounds for a specific session"""
        try:
            # TODO: rounds does not exist on session object
            active_round = session.rounds.filter(status='active').first()

            if active_round:
                if active_round.get_phase() == 'blue' and timezone.now() >= active_round.start_date + timedelta(
                        days=session.rotation_period):
                    self._handle_red_phase_transition(session, active_round)
                elif timezone.now() >= active_round.start_date + timedelta(days=session.rotation_period * 2):
                    self._complete_round(active_round)

            planned_round = session.rounds.filter(status='planned', start_date__lte=timezone.now()).first()

            if planned_round:
                self._start_round(planned_round)
        except Exception as e:
            logger.error(f"Error processing session {session.name} rounds: {e}")

    def _handle_red_phase_transition(self, session: GameSession, phase: GamePhase):
        """Handle transition from blue to red phase"""
        try:
            teams = session.get_teams()

            if phase.is_second_phase():
                success = self.matchmaking_service.create_random_red_assignments(session, teams, phase)
            else:
                success = self.matchmaking_service.create_swiss_assignments(session, teams)

            if not success:
                logger.error(f"Failed to create red phase assignments for round {phase.get_phase_number_display()}")
        except Exception as e:
            logger.error(f"Error handling red phase transition: {e}")

    def _start_round(self, phase: GamePhase):
        """Start a planned round"""
        try:
            with transaction.atomic():
                session = phase.session
                teams = session.get_teams()

                success = self.matchmaking_service.create_round_assignments(session, teams)

                if success:
                    phase.status = 'active'
                    phase.save()
                    logger.info(f"Started round {phase.get_phase_number_display()} for session {session.name}")
                else:
                    logger.error(f"Failed to create assignments for round {phase.get_phase_number_display()}")

        except Exception as e:
            logger.error(f"Error starting round: {e}")

    @staticmethod
    def _complete_round(phase: GamePhase):
        """Complete an active round"""
        try:
            with transaction.atomic():
                phase.status = 'completed'
                phase.save()
                logger.info(f"Completed round {phase.get_phase_number_display()} for session {phase.session.name}")

        except Exception as e:
            logger.error(f"Error completing round: {e}")

    @staticmethod
    def schedule_next_round(session: GameSession):
        """Schedule the next round for a session based on the current round"""
        try:
            current_phase = session.phases.order_by('-phase_number').first()
            template = session.template

            if not current_phase:
                start_date = session.start_date
            else:
                start_date = current_phase.start_date + timedelta(days=session.rotation_period * 2)

            phase = GamePhase.objects.create(
                session=session,
                template=template,
                status='planned',
                phase_number=PhaseNumber.FIRST if not current_phase else PhaseNumber.SECOND,
                start_date=start_date,
            )

            logger.info(f"Scheduled phase {phase.get_phase_number_display()} for session {session.name}")
            return phase
        except Exception as e:
            logger.error(f"Error scheduling next phase for session {session.name}: {str(e)}")
            return None
