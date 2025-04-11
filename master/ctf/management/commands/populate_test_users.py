import sys

from django.core.management.base import BaseCommand

from ctf.models import User
from scripts.populate_users import populate_users


class Command(BaseCommand):
    help = "Populate test users from test-users.txt"

    def handle(self, *args, **options):
        if User.objects.filter(is_staff=False).count() == 0:
            populate_users(stdout=self.stdout)
        else:
            self.stdout.write("Test users can only be imported if no regular users exist")
