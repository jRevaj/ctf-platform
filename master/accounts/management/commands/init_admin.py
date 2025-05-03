from django.core.management.base import BaseCommand

from accounts.models import User
from core import settings


class Command(BaseCommand):
    help = "Initialize admin accounts"

    def handle(self, *args, **options):
        if User.objects.count() == 0:
            for user in settings.ADMINS:
                username = user[0].replace(" ", "")
                email = user[1]
                password = "admin"
                print("Creating account for %s (%s)" % (username, email))
                admin = User.objects.create_superuser(email=email, username=username, password=password)
                admin.is_active = True
                admin.is_staff = True
                admin.save()
        else:
            print("Admin accounts can only be initialized if no Accounts exist")
