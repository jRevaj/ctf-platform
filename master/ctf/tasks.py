import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from ctf.models import GameSession, Team, GamePhase, ChallengeDeployment
from ctf.models.challenge import DeploymentAccess
from ctf.models.enums import GameSessionStatus, TeamRole, ContainerStatus
from ctf.models.settings import GlobalSettings
from ctf.services import DeploymentService
from ctf.services.container_service import ContainerService
from ctf.services.docker_service import DockerService
from ctf.services.matchmaking_service import MatchmakingService
from ctf.utils import is_first_session_for_teams

logger = logging.getLogger(__name__)


@shared_task
def process_sessions():
    """Process planned sessions that are ready to start
    
    This task checks for sessions that are planned to start at the current time
    and creates round assignments for them.
    """
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
    """Process phase transitions for active sessions
    
    This task checks for overdue phases and transitions to the next phase.
    It handles both the transition from blue phase to red phase and the transition from red phase to completed session.
    """
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
            red_phase = session.phases.filter(
                status=GameSessionStatus.ACTIVE,
                phase_name=TeamRole.RED,
                end_date__lte=timezone.now(),
            ).first()

            if red_phase:
                logger.info(f"Red phase overdue for session: {session.name}, completing session")
                session.status = GameSessionStatus.COMPLETED
                session.save(update_fields=["status"])
                continue

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
                    success = matchmaking_service.create_swiss_assignments(session, red_phase, teams,
                                                                           settings.number_of_tiers)

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


@shared_task
def check_inactive_deployments():
    """Check for inactive deployments and stop them if no active SSH connections.
    
    A deployment is considered inactive when:
    1. It has no active SSH connections (has_active_connections=False)
    2. Its last_activity timestamp is older than the timeout setting
    3. It has no active access records in the database
    4. All of its containers haven't had any activity in the timeout period
    """
    logger.info("Running check_inactive_deployments task")
    container_service = ContainerService()

    try:
        settings = GlobalSettings.get_settings()
        if not settings.enable_auto_container_shutdown:
            logger.warning("Auto-container shutdown disabled")
            return

        cutoff_time = timezone.now() - timedelta(minutes=settings.inactive_container_timeout)

        inactive_deployments = ChallengeDeployment.objects.filter(
            has_active_connections=False,
            last_activity__lt=cutoff_time,
            containers__status=ContainerStatus.RUNNING
        ).distinct()

        inactive_deployments = inactive_deployments.exclude(
            access_records__is_active=True
        )

        truly_inactive_deployments = []
        for deployment in inactive_deployments:
            containers = deployment.containers.filter(status=ContainerStatus.RUNNING)

            has_recent_activity = False
            for container in containers:
                if container.last_activity >= cutoff_time:
                    has_recent_activity = True
                    logger.debug(f"Container {container.id} in deployment {deployment.id} has recent activity")
                    break

            if not has_recent_activity:
                truly_inactive_deployments.append(deployment)
                logger.debug(f"Deployment {deployment.id} confirmed inactive - all containers inactive")

        if not truly_inactive_deployments:
            logger.info("No inactive deployments found")
            return

        logger.info(f"Stopping {len(truly_inactive_deployments)} inactive deployments")

        for deployment in truly_inactive_deployments:
            logger.info(f"Stopping inactive deployment {deployment.id} (last activity: {deployment.last_activity})")
            containers = deployment.containers.filter(status=ContainerStatus.RUNNING)
            for container in containers:
                container_service.stop_container(container)

    except Exception as e:
        logger.error(f"Error checking inactive deployments: {e}")


@shared_task()
def monitor_ssh_connections():
    """Monitor SSH connections across all deployments
    
    This task checks for active SSH connections across all deployments
    and updates the deployment's has_active_connections flag accordingly.
    It uses the docker_service to check for active SSH connections and the deployment_service to record and end access sessions.
    """
    logger.info("Running monitor_ssh_connections task")
    docker_service = DockerService()
    deployment_service = DeploymentService()

    try:
        deployments = ChallengeDeployment.objects.filter(
            containers__status=ContainerStatus.RUNNING
        ).distinct().prefetch_related('containers', 'assignments')
        logger.info(f"Found {len(deployments)} deployments")

        for deployment in deployments:
            try:
                logger.info(f"Checking active SSH connections for deployment {deployment.id}")
                has_connections = False
                containers = deployment.containers.filter(status=ContainerStatus.RUNNING)

                active_db_sessions = DeploymentAccess.objects.filter(
                    deployment=deployment,
                    is_active=True
                ).values_list('session_id', flat=True)
                active_db_sessions = set(active_db_sessions)

                all_active_docker_sessions = set()
                container_session_map = {}
                active_containers = set()

                session_type_mapping = {
                    sid: sid.split('-')[1] if '-' in sid and len(sid.split('-')) > 1 else 'unknown'
                    for sid in active_db_sessions
                }

                for container in containers:
                    container_active_sessions = docker_service.check_active_ssh_sessions(container.docker_id)

                    valid_sessions = []
                    for session_id in container_active_sessions:
                        if not session_id or not isinstance(session_id, str):
                            continue

                        if '-' in session_id:
                            valid_sessions.append(session_id)
                        else:
                            logger.warning(f"Skipping invalid session ID: {session_id}")

                    for session_id in valid_sessions:
                        container_session_map[session_id] = container

                    if valid_sessions:
                        active_containers.add(container.id)

                    all_active_docker_sessions.update(valid_sessions)

                    if valid_sessions:
                        has_connections = True

                invalid_sessions = [sid for sid in active_db_sessions
                                    if not ('-' in sid and len(sid.split('-')) > 1)]
                for session_id in invalid_sessions:
                    logger.warning(f"Ending invalid deployment access session: {session_id}")
                    deployment_service.end_deployment_access(deployment, session_id)

                active_docker_session_by_type = {}
                for session_id in all_active_docker_sessions:
                    session_type = session_id.split('-')[1] if len(session_id.split('-')) > 1 else 'unknown'
                    if session_type not in active_docker_session_by_type:
                        active_docker_session_by_type[session_type] = []
                    active_docker_session_by_type[session_type].append(session_id)

                matched_db_sessions = set()

                for session_id in all_active_docker_sessions:
                    if session_id in active_db_sessions:
                        matched_db_sessions.add(session_id)

                        container = container_session_map.get(session_id)
                        if container:
                            container.update_activity()
                        continue

                    session_parts = session_id.split('-')
                    if len(session_parts) <= 1:
                        continue

                    session_type = session_parts[1]

                    found_match = False
                    for db_session in active_db_sessions:
                        if db_session in matched_db_sessions:
                            continue

                        db_session_type = session_type_mapping.get(db_session)
                        if db_session_type == session_type:
                            matched_db_sessions.add(db_session)
                            found_match = True

                            container = container_session_map.get(session_id)
                            if container:
                                container.update_activity()

                            logger.debug(f"Matched docker session {session_id} to existing DB session {db_session}")
                            break

                    if not found_match:
                        container = container_session_map.get(session_id)
                        if container:
                            team = container.red_team if container.red_team else container.blue_team
                            if team:
                                logger.info(f"Recording new deployment access session {session_id}")
                                deployment_service.record_deployment_access(
                                    deployment=deployment,
                                    team=team,
                                    container=container,
                                    session_id=session_id
                                )
                                container.update_activity()

                for container in containers:
                    if container.id in active_containers:
                        container.update_activity()

                for session_id in active_db_sessions:
                    if session_id not in matched_db_sessions and session_id not in invalid_sessions:
                        logger.info(f"Ending deployment access session {session_id}")
                        deployment_service.end_deployment_access(deployment, session_id)

                if has_connections != deployment.has_active_connections:
                    deployment.has_active_connections = has_connections
                    deployment.last_activity = timezone.now()
                    deployment.save(update_fields=['has_active_connections', 'last_activity'])

            except Exception as e:
                logger.error(f"Error monitoring deployment {deployment.pk}: {e}")

    except Exception as e:
        logger.error(f"Error monitoring SSH connections: {e}")
