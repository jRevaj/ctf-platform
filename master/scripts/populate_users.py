import os
import sys
from pathlib import Path

import django

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from ctf.models import User


def populate_users(stdout=sys.stdout):
    credentials_file = project_root / 'test-users.txt'

    if not credentials_file.exists():
        stdout.write(f"Credentials file not found at {credentials_file}\n")
        return

    with open(credentials_file, 'r') as f:
        for line in f:
            if not line.strip():
                continue

            parts = line.strip().split(',')
            if len(parts) != 4:
                stdout.write(f"Skipping invalid line: {line.strip()}\n")
                continue

            username, email, password, ssh_key = parts

            if User.objects.filter(username=username).exists():
                stdout.write(f"User {username} already exists, skipping...\n")
                continue

            try:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    ssh_public_key=ssh_key
                )
                stdout.write(f"Created user: {user.username}\n")
            except Exception as e:
                stdout.write(f"Error creating user {username}: {str(e)}\n")


if __name__ == '__main__':
    stdout = sys.stdout
    stdout.write("Starting test users import...\n")
    populate_users(stdout)
    stdout.write("Test users import completed.\n")
