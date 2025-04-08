import logging

from django.core.management.base import BaseCommand

from ctf.models import User
from scripts.populate_users import populate_users

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Populate test users from test-users.txt"

    def handle(self, *args, **options):
        if User.objects.filter(is_staff=False).count() == 0:
            populate_users()
        else:
            logger.info("Test users can only be imported if no regular users exist")
