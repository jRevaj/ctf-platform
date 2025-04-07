import logging

from django.core.management.base import BaseCommand

from ctf.tasks import process_sessions

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Manually trigger processing of planned game sessions that are ready to start"

    def handle(self, *args, **options):
        process_sessions.apply()
        logger.info("Finished process_sessions command")
