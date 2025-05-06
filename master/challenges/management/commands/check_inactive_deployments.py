import logging

from django.core.management.base import BaseCommand

from challenges.tasks import check_inactive_deployments

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Manually trigger checking inactive deployments"

    def handle(self, *args, **options):
        check_inactive_deployments.apply()
        logger.info("Finished check_inactive_deployments command")
