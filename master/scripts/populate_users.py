import os
import sys
from pathlib import Path

import django

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from ctf.models import User


def populate_users():
    credentials_file = project_root / 'test-users.txt'

    if not credentials_file.exists():
        sys.stderr(f"Credentials file not found at {credentials_file}")
        return

    with open(credentials_file, 'r') as f:
        for line in f:
            if not line.strip():
                continue

            parts = line.strip().split(',')
            if len(parts) != 4:
                sys.stdout(f"Skipping invalid line: {line.strip()}")
                continue

            username, email, password, ssh_key = parts

            if User.objects.filter(username=username).exists():
                sys.stdout(f"User {username} already exists, skipping...")
                continue

            try:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    ssh_public_key=ssh_key
                )
                sys.stdout(f"Created user: {user.username}")
            except Exception as e:
                sys.stdout(f"Error creating user {username}: {str(e)}")


if __name__ == '__main__':
    sys.stdout("Starting test users import...")
    populate_users()
    sys.stdout("Test users import completed.")
