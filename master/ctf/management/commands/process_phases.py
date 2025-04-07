import logging

from django.core.management.base import BaseCommand

from ctf.tasks import process_phases

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Manually trigger processing automatic rotations"

    def handle(self, *args, **options):
        process_phases.apply()
        logger.info("Finished process_phases commands")
