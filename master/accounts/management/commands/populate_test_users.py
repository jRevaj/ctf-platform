from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = "Populate test users from test-users.txt"

    def handle(self, *args, **options):
        if User.objects.filter(is_staff=False).count() == 0:
            self.stdout.write("Starting test users import...\n")
            credentials_file = Path(settings.BASE_DIR) / 'test-users.txt'

            if not credentials_file.exists():
                self.stdout.write(f"Credentials file not found at {credentials_file}\n")
                return

            with open(credentials_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue

                    parts = line.strip().split(',')
                    if len(parts) != 4:
                        self.stdout.write(f"Skipping invalid line: {line.strip()}\n")
                        continue

                    username, email, password, ssh_key = parts

                    if User.objects.filter(username=username).exists():
                        self.stdout.write(f"User {username} already exists, skipping...\n")
                        continue

                    try:
                        user = User.objects.create_user(
                            username=username,
                            email=email,
                            password=password,
                            ssh_public_key=ssh_key
                        )
                        self.stdout.write(f"Created user: {user.username}\n")
                    except Exception as e:
                        self.stdout.write(f"Error creating user {username}: {str(e)}\n")
            self.stdout.write("Test users import completed.\n")
        else:
            self.stdout.write("Test users can only be imported if no regular users exist")
