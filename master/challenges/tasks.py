import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from challenges.models import ChallengeDeployment, DeploymentAccess
from challenges.models.enums import ContainerStatus
from challenges.services import ContainerService, DockerService, DeploymentService
from ctf.models.settings import GlobalSettings

logger = logging.getLogger(__name__)


@shared_task
def check_inactive_deployments():
    """Check for inactive deployments and stop them if no active SSH connections.

    A deployment is considered inactive when:
    1. It has no active SSH connections (has_active_connections=False)
    2. Its last_activity timestamp is older than the timeout setting
    3. It has no active access records in the database
    4. All of its containers haven't had any activity in the timeout period

    Raises:
        Exception: If there's an error checking or stopping inactive deployments
    """
    logger.info("Running check_inactive_deployments task")
    settings = GlobalSettings.get_settings()
    if not settings.enable_auto_container_shutdown:
        logger.warning("Auto-container shutdown disabled")
        return

    container_service = ContainerService()
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
    failed_deployments = []

    for deployment in truly_inactive_deployments:
        try:
            logger.info(f"Stopping inactive deployment {deployment.id} (last activity: {deployment.last_activity})")
            containers = deployment.containers.filter(status=ContainerStatus.RUNNING)

            for container in containers:
                try:
                    container_service.stop_container(container)
                except Exception as e:
                    error_msg = f"Failed to stop container {container.id} in deployment {deployment.id}: {str(e)}"
                    logger.error(error_msg)
                    failed_deployments.append((deployment.id, error_msg))

        except Exception as e:
            error_msg = f"Error processing deployment {deployment.id}: {str(e)}"
            logger.error(error_msg)
            failed_deployments.append((deployment.id, error_msg))

    if failed_deployments:
        error_details = "\n".join([f"- Deployment {id}: {error}" for id, error in failed_deployments])
        raise Exception(f"Failed to stop some inactive deployments:\n{error_details}")

    logger.info("Successfully processed all inactive deployments")


@shared_task()
def monitor_ssh_connections():
    """Monitor SSH connections across all deployments

    This task checks for active SSH connections across all deployments
    and updates the deployment's has_active_connections flag accordingly.
    It uses the docker_service to check for active SSH connections and the deployment_service to record and end access sessions.
    """
    logger.info("Running monitor_ssh_connections task")
    container_service = ContainerService()
    docker_service = DockerService()
    deployment_service = DeploymentService()

    try:
        deployments = ChallengeDeployment.objects.filter(
            containers__status=ContainerStatus.RUNNING
        ).distinct().prefetch_related(
            'containers',
            'assignments',
            'access_records'
        ).select_related(
            'template'
        )

        active_access_records = DeploymentAccess.objects.filter(
            is_active=True,
            deployment__in=deployments
        ).select_related('team', 'deployment')

        active_db_sessions_map = {}
        session_type_mapping = {}
        for record in active_access_records:
            if record.session_id:
                sessions = record.session_id.split(',')
                active_db_sessions_map[record.deployment_id] = set(sessions)
                for session_id in sessions:
                    if '-' in session_id and len(session_id.split('-')) > 1:
                        session_type_mapping[session_id] = session_id.split('-')[1]

        logger.info(f"Found {len(deployments)} active deployments")

        for deployment in deployments:
            try:
                logger.info(f"Checking active SSH connections for deployment {deployment.id}")
                has_connections = False

                running_containers = list(deployment.containers.filter(status=ContainerStatus.RUNNING))
                if not running_containers:
                    continue

                active_db_sessions = active_db_sessions_map.get(deployment.id, set())

                all_active_docker_sessions = set()
                container_session_map = {}
                active_containers = set()
                matched_db_sessions = set()

                for container in running_containers:
                    container_active_sessions = docker_service.check_active_ssh_sessions(container.docker_id)

                    valid_sessions = {
                        sid for sid in container_active_sessions
                        if sid and isinstance(sid, str) and '-' in sid
                    }

                    for session_id in valid_sessions:
                        container_session_map[session_id] = container
                        all_active_docker_sessions.add(session_id)

                    if valid_sessions:
                        active_containers.add(container.id)
                        has_connections = True

                invalid_sessions = {
                    sid for sid in active_db_sessions
                    if not ('-' in sid and len(sid.split('-')) > 1)
                }

                for session_id in invalid_sessions:
                    logger.warning(f"Ending invalid deployment access session: {session_id}")
                    deployment_service.end_deployment_access(deployment, session_id)

                for session_id in all_active_docker_sessions:
                    if session_id in active_db_sessions:
                        matched_db_sessions.add(session_id)
                        container = container_session_map.get(session_id)
                        if container:
                            team = container.red_team if container.red_team else container.blue_team
                            if team and deployment_service.has_exceeded_time_limit(team, deployment):
                                logger.info(f"Team {team.name} has exceeded time limit for deployment {deployment.id}")
                                for dep_container in running_containers:
                                    container_service.kill_ssh_session(dep_container, True)
                                deployment_service.end_deployment_access(deployment, session_id)
                                continue
                            container.update_activity()
                        logger.debug(f"Matched docker session {session_id} to existing DB session {db_session}")
                        continue

                    session_parts = session_id.split('-')
                    if len(session_parts) <= 1:
                        continue

                    session_type = session_parts[1]
                    found_match = False

                    for db_session in active_db_sessions - matched_db_sessions:
                        db_session_type = session_type_mapping.get(db_session)
                        if db_session_type == session_type:
                            matched_db_sessions.add(db_session)
                            found_match = True
                            container = container_session_map.get(session_id)
                            if container:
                                team = container.red_team if container.red_team else container.blue_team
                                if team and deployment_service.has_exceeded_time_limit(team, deployment):
                                    logger.info(
                                        f"Team {team.name} has exceeded time limit for deployment {deployment.id}")
                                    for dep_container in running_containers:
                                        container_service.kill_ssh_session(dep_container, True)
                                    deployment_service.end_deployment_access(deployment, session_id)
                                    continue
                                container.update_activity()
                            logger.debug(f"Matched docker session {session_id} to existing DB session {db_session}")
                            break

                    if not found_match:
                        container = container_session_map.get(session_id)
                        if container:
                            team = container.red_team if container.red_team else container.blue_team
                            if team:
                                if deployment_service.has_exceeded_time_limit(team, deployment):
                                    logger.info(
                                        f"Team {team.name} has exceeded time limit for deployment {deployment.id}")
                                    for dep_container in running_containers:
                                        container_service.kill_ssh_session(dep_container, True)
                                    deployment_service.end_deployment_access(deployment, session_id)
                                    continue

                                logger.info(f"Recording new deployment access session {session_id}")
                                deployment_service.record_deployment_access(
                                    deployment=deployment,
                                    team=team,
                                    container=container,
                                    session_id=session_id
                                )
                                container.update_activity()

                for session_id in active_db_sessions - matched_db_sessions - invalid_sessions:
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
