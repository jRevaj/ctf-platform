import logging

from django.core.management.base import BaseCommand

from challenges.tasks import monitor_ssh_connections

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Manually trigger monitoring ssh connections"

    def handle(self, *args, **options):
        monitor_ssh_connections.apply()
        logger.info("Finished monitor_ssh_connections command")
