import logging
from datetime import timedelta

from django.utils import timezone

from challenges.models.challenge import DeploymentAccess
from challenges.services import ContainerService, DockerService
from ctf.models.enums import GameSessionStatus

logger = logging.getLogger(__name__)


class DeploymentService:
    """Business logic for deployment wide operations"""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DeploymentService, cls).__new__(cls)
            cls._instance.container_service = ContainerService()
            cls._instance.docker = DockerService()
        return cls._instance

    def start_deployment(self, deployment) -> bool:
        """Start all containers in a deployment"""
        try:
            containers = deployment.containers.all()
            logger.info(f"Starting {len(containers)} containers for deployment {deployment.pk}")

            success = True
            for container in containers:
                if not container.is_running():
                    logger.info(f"Container {container.name} is not running - trying to start it")
                    if not self.container_service.start_container(container):
                        logger.warning(f"Failed to start container {container.name}")
                        success = False
                else:
                    logger.info(f"Container {container.name} is already running")

            deployment.update_activity()
            return success
        except Exception as e:
            logger.error(f"Failed to start deployment {deployment.pk}: {e}")
            return False

    def stop_deployment(self, deployment) -> bool:
        """Stop all containers in a deployment"""
        try:
            containers = deployment.containers.all()
            logger.info(f"Stopping {len(containers)} containers for deployment {deployment.pk}")

            success = True
            for container in containers:
                if container.is_running():
                    if not self.container_service.stop_container(container):
                        logger.warning(f"Failed to stop container {container.name}")
                        success = False
                else:
                    logger.info(f"Container {container.name} is already stopped")

            deployment.has_active_connections = False
            deployment.save(update_fields=['has_active_connections'])
            return success
        except Exception as e:
            logger.error(f"Failed to stop deployment {deployment.pk}: {e}")
            return False

    def sync_deployment_status(self, deployment) -> bool:
        """Sync status of all containers in a deployment"""
        try:
            containers = deployment.containers.all()
            logger.info(f"Syncing status for {len(containers)} containers in deployment {deployment.pk}")

            success = True
            for container in containers:
                if not self.container_service.sync_container_status(container):
                    logger.warning(f"Failed to sync container {container.name}")
                    success = False

            return success
        except Exception as e:
            logger.error(f"Failed to sync deployment {deployment.pk}: {e}")
            return False

    @staticmethod
    def record_deployment_access(deployment, team, container=None, session_id=None) -> bool:
        """Record a new SSH access to the deployment"""
        try:
            existing_access = DeploymentAccess.objects.filter(
                deployment=deployment,
                team=team,
                session_id=session_id,
                is_active=True
            ).first()

            if existing_access:
                if container and container.id not in existing_access.containers:
                    containers = existing_access.containers
                    containers.append(container.id)
                    existing_access.containers = containers
                    existing_access.save(update_fields=['containers'])
                    logger.debug(f"Added container {container.id} to existing access record {existing_access.id}")
                return True

            containers_list = [container.id] if container else []
            DeploymentAccess.objects.create(
                deployment=deployment,
                team=team,
                session_id=session_id,
                access_type="SSH",
                is_active=True,
                containers=containers_list
            )

            deployment.update_activity()
            logger.info(f"Recorded new deployment access for team {team.id}, deployment {deployment.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to record deployment access: {e}")
            return False

    @staticmethod
    def end_deployment_access(deployment, session_id: str) -> bool:
        """End an SSH access session at deployment level"""
        try:
            access = DeploymentAccess.objects.filter(
                deployment=deployment,
                session_id=session_id,
                is_active=True
            ).first()

            if access:
                access.end_session()
                logger.info(f"Ended deployment access session {session_id} for deployment {deployment.id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to end deployment access: {e}")
            return False

    def has_exceeded_time_limit(self, team, deployment):
        """Check if team has exceeded their time limit for this deployment"""
        game_session = deployment.assignments.filter(
            team=team,
            session__status=GameSessionStatus.ACTIVE
        ).first()

        if not game_session or not game_session.session.enable_time_restrictions:
            return False

        time_spent = self.get_team_total_access_time_for_deployment(team, deployment)
        max_time = game_session.session.get_max_time_for_role(game_session.role)

        logger.info(f"Time spent: {time_spent} minutes, Max time: {max_time} minutes")
        return max_time > 0 and time_spent >= max_time

    @staticmethod
    def get_team_total_access_time_for_deployment(team, deployment):
        """Get total time spent by team on this deployment in minutes"""
        game_session = deployment.assignments.filter(
            team=team,
            session__status=GameSessionStatus.ACTIVE
        ).first()

        if not game_session or not game_session.session.enable_time_restrictions:
            return 0

        access_records = DeploymentAccess.objects.filter(
            deployment=deployment,
            team=team
        ).order_by('start_time')

        time_periods = []
        for record in access_records:
            if record.is_active:
                end_time = timezone.now()
            else:
                end_time = record.end_time

            time_periods.append((record.start_time, end_time))

        if not time_periods:
            return 0

        merged_periods = []
        current_start, current_end = time_periods[0]
        for start, end in time_periods[1:]:
            if start <= current_end:
                current_end = max(current_end, end)
            else:
                merged_periods.append((current_start, current_end))
                current_start, current_end = start, end

        merged_periods.append((current_start, current_end))

        total_duration = timedelta(0)
        for start, end in merged_periods:
            total_duration += end - start

        return total_duration.total_seconds() / 60

    def get_remaining_time_for_deployment(self, team, deployment):
        """Get remaining time in minutes for team's deployment access"""
        game_session = deployment.assignments.filter(
            team=team,
            session__status=GameSessionStatus.ACTIVE
        ).first()

        if not game_session or not game_session.session.enable_time_restrictions:
            return 0

        max_time = game_session.session.get_max_time_for_role(game_session.role)
        if max_time <= 0:
            return 0

        time_spent = self.get_team_total_access_time_for_deployment(team, deployment)
        remaining = max_time - time_spent
        return max(0, remaining)
