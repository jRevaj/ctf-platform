import logging

from celery import Celery
from celery.schedules import crontab

from ctf.models.settings import GlobalSettings

logger = logging.getLogger(__name__)


def parse_cron_string(cron_string):
    """
    Parse a cron string into components for celery crontab
    
    Format: minute hour day_of_month month day_of_week
    """
    try:
        parts = cron_string.split()
        if len(parts) != 5:
            logger.error(f"Invalid cron string format: {cron_string}")
            return crontab()
        
        minute, hour, day_of_month, month, day_of_week = parts
        
        return crontab(
            minute=minute,
            hour=hour, 
            day_of_month=day_of_month, 
            month_of_year=month, 
            day_of_week=day_of_week
        )
    except Exception as e:
        logger.error(f"Error parsing cron string '{cron_string}': {e}")
        return crontab()


def configure_task_schedules(app):
    """
    Configure dynamic task schedules based on GlobalSettings
    
    Call this function after Celery app is created, but before it's used
    """
    try:
        settings_obj = GlobalSettings.get_settings()

        beat_schedule = {
            'process-sessions': {
                'task': 'ctf.tasks.process_sessions',
                'schedule': parse_cron_string(settings_obj.process_sessions_cron),
            },
            'process-phases': {
                'task': 'ctf.tasks.process_phases',
                'schedule': parse_cron_string(settings_obj.process_phases_cron),
            },
            'check-inactive-deployments': {
                'task': 'ctf.tasks.check_inactive_deployments',
                'schedule': parse_cron_string(settings_obj.check_inactive_deployments_cron),
            },
            'monitor-ssh-connections': {
                'task': 'ctf.tasks.monitor_ssh_connections',
                'schedule': parse_cron_string(settings_obj.monitor_ssh_connections_cron),
            },
        }

        app.conf.beat_schedule = beat_schedule
        logger.info("Updated Celery beat schedule with cron expressions from settings")

    except Exception as e:
        logger.error(f"Failed to configure dynamic task schedules: {e}")


def update_celery_schedules():
    """
    Utility function to update Celery schedules at runtime
    
    This can be called after settings are changed to update the schedule
    without restarting the Celery workers.
    """
    try:
        app = Celery()

        configure_task_schedules(app)

        return True
    except Exception as e:
        logger.error(f"Failed to update Celery schedules: {e}")
        return False
