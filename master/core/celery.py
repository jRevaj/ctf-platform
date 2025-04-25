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
# These will be overridden by settings from GlobalSettings
default_schedule = {
    'process_sessions': {
        'task': 'ctf.tasks.process_sessions',
        'schedule': crontab(minute='0', hour='0'),  # Daily at midnight
    },
    'process_phases': {
        'task': 'ctf.tasks.process_phases',
        'schedule': crontab(minute='0', hour='1'),  # Daily at 1:00 AM
    },
    'check_inactive_deployments': {
        'task': 'ctf.tasks.check_inactive_deployments',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    'monitor_ssh_connections': {
        'task': 'ctf.tasks.monitor_ssh_connections',
        'schedule': crontab(minute='*/2'),  # Every 2 minutes
    },
}

# Set default schedule, will be updated by configure_task_schedules
app.conf.beat_schedule = default_schedule

# Apply dynamic scheduling from database
try:
    # Need to run after Django is fully loaded
    @app.on_after_configure.connect
    def setup_periodic_tasks(sender, **kwargs):
        # Import here to avoid import errors during initial startup
        from ctf.utils.scheduler import configure_task_schedules
        configure_task_schedules(sender)
except Exception as e:
    # Log the error but continue with default schedule
    print(f"Error configuring dynamic task schedules: {e}")
    print("Using default schedule instead")
