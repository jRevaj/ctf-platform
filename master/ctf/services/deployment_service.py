import logging

from ctf.models.challenge import DeploymentAccess
from ctf.services.container_service import ContainerService
from ctf.services.docker_service import DockerService

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
