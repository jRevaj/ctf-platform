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

# Schedule tasks
app.conf.beat_schedule = {
    'process_sessions': {
        'task': 'ctf.tasks.process_sessions',
        'schedule': crontab(minute='*/2'),
    },
    'process_phases': {
        'task': 'ctf.tasks.process_phases',
        'schedule': crontab(minute='*/3'),
    }
}
