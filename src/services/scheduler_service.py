"""APScheduler service for managing standup and feedback jobs"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, time as dt_time
from src.config import config
from src.utils.logger import setup_logger
from src.database.session import get_session
from src.models.client import Client
from src.models.standup_config import StandupConfig
from src.models.feedback_config import FeedbackConfig

logger = setup_logger(__name__)

# Global scheduler instance
scheduler = None


def init_scheduler():
    """Initialize and start the APScheduler"""
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler already initialized")
        return scheduler

    # Configure job stores and executors
    # Use memory store for SQLite (simpler), SQLAlchemy for PostgreSQL
    if config.DATABASE_URL.startswith('sqlite'):
        from apscheduler.jobstores.memory import MemoryJobStore
        jobstores = {
            'default': MemoryJobStore()
        }
        logger.info("Using in-memory job store (SQLite mode)")
    else:
        jobstores = {
            'default': SQLAlchemyJobStore(url=config.DATABASE_URL)
        }

    executors = {
        'default': ThreadPoolExecutor(20)
    }

    job_defaults = {
        'coalesce': True,  # Combine missed runs into one
        'max_instances': 3,  # Max concurrent instances per job
        'misfire_grace_time': 900  # 15 minutes grace period
    }

    # Create scheduler
    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone='UTC'
    )

    # Start scheduler
    scheduler.start()
    logger.info("APScheduler started successfully")

    # Load existing jobs from database
    sync_jobs_from_database()

    return scheduler


def sync_jobs_from_database():
    """
    Load all active client jobs from database and schedule them

    This ensures jobs persist across restarts
    """
    session = get_session()
    try:
        # Load active standup configs
        standup_configs = session.query(StandupConfig).join(Client).filter(
            StandupConfig.is_paused == False,
            Client.is_active == True
        ).all()

        logger.info(f"Found {len(standup_configs)} active standup configurations")
        for config in standup_configs:
            add_standup_job(config)

        # Load active feedback configs
        feedback_configs = session.query(FeedbackConfig).join(Client).filter(
            FeedbackConfig.is_enabled == True,
            Client.is_active == True
        ).all()

        logger.info(f"Found {len(feedback_configs)} active feedback configurations")
        for config in feedback_configs:
            add_feedback_job(config)

    except Exception as e:
        logger.error(f"Failed to sync jobs from database: {e}")
    finally:
        session.close()


def add_standup_job(standup_config: StandupConfig):
    """
    Add or update a standup job in the scheduler

    Args:
        standup_config: StandupConfig instance with scheduling details
    """
    if not scheduler:
        logger.error("Scheduler not initialized")
        return

    job_id = standup_config.client.job_id_standup

    # Remove existing job if present
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    # Create trigger based on schedule type
    if standup_config.schedule_type == 'daily':
        trigger = CronTrigger(
            hour=standup_config.schedule_time.hour,
            minute=standup_config.schedule_time.minute,
            timezone=standup_config.client.timezone
        )
    elif standup_config.schedule_type == 'monday_only':
        trigger = CronTrigger(
            day_of_week='mon',
            hour=standup_config.schedule_time.hour,
            minute=standup_config.schedule_time.minute,
            timezone=standup_config.client.timezone
        )
    else:
        logger.error(f"Invalid schedule type: {standup_config.schedule_type}")
        return

    # Add job to scheduler
    scheduler.add_job(
        func=send_standup_job,
        trigger=trigger,
        id=job_id,
        args=[standup_config.client.workspace_id, standup_config.client.id],
        replace_existing=True,
        name=f"Standup for {standup_config.client.display_name or standup_config.client.slack_user_id}"
    )

    logger.info(f"Scheduled standup job: {job_id} ({standup_config.schedule_type} at {standup_config.schedule_time})")


def add_feedback_job(feedback_config: FeedbackConfig):
    """
    Add or update a Friday feedback job in the scheduler

    Args:
        feedback_config: FeedbackConfig instance with scheduling details
    """
    if not scheduler:
        logger.error("Scheduler not initialized")
        return

    job_id = feedback_config.client.job_id_feedback

    # Remove existing job if present
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    # Create Friday trigger
    trigger = CronTrigger(
        day_of_week='fri',
        hour=feedback_config.schedule_time.hour,
        minute=feedback_config.schedule_time.minute,
        timezone=feedback_config.client.timezone
    )

    # Add job to scheduler
    scheduler.add_job(
        func=send_feedback_job,
        trigger=trigger,
        id=job_id,
        args=[feedback_config.client.workspace_id, feedback_config.client.id],
        replace_existing=True,
        name=f"Feedback for {feedback_config.client.display_name or feedback_config.client.slack_user_id}"
    )

    logger.info(f"Scheduled feedback job: {job_id} (Fridays at {feedback_config.schedule_time})")


def remove_standup_job(client_id: int, workspace_id: int):
    """Remove a standup job from the scheduler"""
    if not scheduler:
        return

    job_id = f"standup_{workspace_id}_{client_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"Removed standup job: {job_id}")


def remove_feedback_job(client_id: int, workspace_id: int):
    """Remove a feedback job from the scheduler"""
    if not scheduler:
        return

    job_id = f"feedback_{workspace_id}_{client_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"Removed feedback job: {job_id}")


def send_standup_job(workspace_id: int, client_id: int):
    """
    Scheduled job function to send standup DM

    This function is called by APScheduler at the configured time

    Args:
        workspace_id: Workspace database ID
        client_id: Client database ID
    """
    try:
        from src.services.standup_service import send_standup_dm
        send_standup_dm(workspace_id, client_id)
    except Exception as e:
        logger.error(f"Failed to send standup (workspace={workspace_id}, client={client_id}): {e}")
        import traceback
        logger.error(traceback.format_exc())


def send_feedback_job(workspace_id: int, client_id: int):
    """
    Scheduled job function to send weekly feedback DM

    This function is called by APScheduler every Friday at the configured time

    Args:
        workspace_id: Workspace database ID
        client_id: Client database ID
    """
    try:
        from src.services.feedback_service import send_feedback_dm
        send_feedback_dm(workspace_id, client_id)
    except Exception as e:
        logger.error(f"Failed to send feedback (workspace={workspace_id}, client={client_id}): {e}")
        import traceback
        logger.error(traceback.format_exc())


def get_scheduled_jobs():
    """Get list of all scheduled jobs"""
    if not scheduler:
        return []

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time,
            'trigger': str(job.trigger)
        })

    return jobs
