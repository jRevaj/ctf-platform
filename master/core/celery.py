import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for celery.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Initialize Celery app
app = Celery('ctf')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Define default schedule as direct crontab instances
# These will be overridden by the database scheduler
app.conf.beat_schedule = {
    'process_sessions': {
        'task': 'ctf.tasks.process_sessions',
        'schedule': crontab(minute=0, hour=0),  # Daily at midnight
    },
    'process_phases': {
        'task': 'ctf.tasks.process_phases',
        'schedule': crontab(minute=0, hour=1),  # Daily at 1:00 AM
    },
    'check_inactive_deployments': {
        'task': 'ctf.tasks.check_inactive_deployments',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    'monitor_ssh_connections': {
        'task': 'ctf.tasks.monitor_ssh_connections',
        'schedule': crontab(minute='1-59/2'),  # Every 2 minutes
    },
}
