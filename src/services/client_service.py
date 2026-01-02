"""Client management service"""

from typing import Optional, List
from datetime import time as dt_time
from sqlalchemy.orm import Session
from src.models.client import Client
from src.models.standup_config import StandupConfig
from src.models.feedback_config import FeedbackConfig
from src.utils.logger import setup_logger
from src.database.session import get_session, db_transaction
from src.services.scheduler_service import add_standup_job, add_feedback_job, remove_standup_job, remove_feedback_job

logger = setup_logger(__name__)


def add_client(
    workspace_id: int,
    slack_user_id: str,
    display_name: str,
    email: Optional[str],
    timezone: str,
    schedule_type: Optional[str],
    schedule_time: dt_time,
    enable_feedback: bool = True
) -> Client:
    """
    Add a new client with configurations

    Args:
        workspace_id: Workspace database ID
        slack_user_id: Slack user ID
        display_name: User's display name
        email: User's email
        timezone: Client timezone
        schedule_type: 'daily', 'monday_only', or None (no standup)
        schedule_time: Time to send standups
        enable_feedback: Whether to enable Friday vibe check

    Returns:
        Created Client instance
    """
    with db_transaction() as session:
        # Create client
        client = Client(
            workspace_id=workspace_id,
            slack_user_id=slack_user_id,
            display_name=display_name,
            email=email,
            timezone=timezone,
            is_active=True
        )
        session.add(client)
        session.flush()  # Get client ID

        # Create standup config only if schedule_type is specified
        if schedule_type:
            standup_config = StandupConfig(
                client_id=client.id,
                schedule_type=schedule_type,
                schedule_time=schedule_time,
                is_paused=False
            )
            session.add(standup_config)
            session.flush()
            add_standup_job(standup_config)

        # Create feedback config if enabled
        if enable_feedback:
            feedback_config = FeedbackConfig(
                client_id=client.id,
                schedule_time=dt_time(15, 0),  # 3 PM default
                is_enabled=True
            )
            session.add(feedback_config)
            session.flush()
            add_feedback_job(feedback_config)

        logger.info(f"Added client: {slack_user_id} (ID: {client.id})")
        return client


def get_client(client_id: int) -> Optional[Client]:
    """Get client by ID"""
    session = get_session()
    try:
        return session.query(Client).filter_by(id=client_id).first()
    finally:
        session.close()


def get_client_by_slack_id(workspace_id: int, slack_user_id: str) -> Optional[Client]:
    """Get client by Slack user ID"""
    session = get_session()
    try:
        return session.query(Client).filter_by(
            workspace_id=workspace_id,
            slack_user_id=slack_user_id
        ).first()
    finally:
        session.close()


def get_workspace_clients(workspace_id: int, active_only: bool = True) -> List[Client]:
    """Get all clients for a workspace"""
    session = get_session()
    try:
        query = session.query(Client).filter_by(workspace_id=workspace_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.all()
    finally:
        session.close()


def pause_client_standups(client_id: int) -> bool:
    """Pause standups for a client"""
    try:
        with db_transaction() as session:
            client = session.query(Client).filter_by(id=client_id).first()
            if client and client.standup_config:
                client.standup_config.is_paused = True
                remove_standup_job(client_id, client.workspace_id)
                logger.info(f"Paused standups for client {client_id}")
                return True
            return False
    except Exception as e:
        logger.error(f"Failed to pause standups: {e}")
        return False


def resume_client_standups(client_id: int) -> bool:
    """Resume standups for a client"""
    try:
        with db_transaction() as session:
            client = session.query(Client).filter_by(id=client_id).first()
            if client and client.standup_config:
                client.standup_config.is_paused = False
                add_standup_job(client.standup_config)
                logger.info(f"Resumed standups for client {client_id}")
                return True
            return False
    except Exception as e:
        logger.error(f"Failed to resume standups: {e}")
        return False


def remove_client(client_id: int) -> bool:
    """Remove a client and all associated data"""
    try:
        with db_transaction() as session:
            client = session.query(Client).filter_by(id=client_id).first()
            if client:
                # Remove scheduled jobs
                remove_standup_job(client_id, client.workspace_id)
                remove_feedback_job(client_id, client.workspace_id)

                # Delete client (cascades to configs and responses)
                session.delete(client)
                logger.info(f"Removed client {client_id}")
                return True
            return False
    except Exception as e:
        logger.error(f"Failed to remove client: {e}")
        return False
