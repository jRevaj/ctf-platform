import os
import sys
from pathlib import Path

import django

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from ctf.models import User
from django.conf import settings
import logging

logger = logging.getLogger('ctf')


def populate_users():
    credentials_file = project_root / 'test-users.txt'

    if not credentials_file.exists():
        logger.error(f"Credentials file not found at {credentials_file}")
        return

    with open(credentials_file, 'r') as f:
        for line in f:
            if not line.strip():
                continue

            parts = line.strip().split(',')
            if len(parts) != 4:
                logger.warning(f"Skipping invalid line: {line.strip()}")
                continue

            username, email, password, ssh_key = parts

            if User.objects.filter(username=username).exists():
                logger.warning(f"User {username} already exists, skipping...")
                continue

            try:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    ssh_public_key=ssh_key
                )
                logger.info(f"Created user: {user.username}")
            except Exception as e:
                logger.error(f"Error creating user {username}: {str(e)}")


if __name__ == '__main__':
    logger.info("Starting test users import...")
    populate_users()
    logger.info("Test users import completed.")
