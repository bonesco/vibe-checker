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


class ClientAlreadyExistsError(Exception):
    """Raised when attempting to add a client that already exists"""
    pass


def add_client(
    workspace_id: int,
    slack_user_id: str,
    display_name: str,
    email: Optional[str],
    timezone: str,
    schedule_type: str,
    schedule_time: dt_time,
    vibe_check_enabled: bool = True
) -> dict:
    """
    Add a new client with default configurations

    Args:
        workspace_id: Workspace database ID
        slack_user_id: Slack user ID
        display_name: User's display name
        email: User's email
        timezone: Client timezone
        schedule_type: 'daily' or 'monday_only'
        schedule_time: Time to send standups
        vibe_check_enabled: Whether to enable Friday vibe checks (default: True)

    Returns:
        Dict with client info: {id, slack_user_id, display_name}

    Raises:
        ClientAlreadyExistsError: If a client with this Slack user ID already exists in the workspace
    """
    client_id = None

    with db_transaction() as session:
        # Check for existing client
        existing = session.query(Client).filter_by(
            workspace_id=workspace_id,
            slack_user_id=slack_user_id
        ).first()
        if existing:
            raise ClientAlreadyExistsError(
                f"User {slack_user_id} is already a client in this workspace"
            )

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

        client_id = client.id

        # Create standup config with client_id directly
        standup_config = StandupConfig(
            client_id=client_id,
            schedule_type=schedule_type,
            schedule_time=schedule_time,
            is_paused=False
        )
        session.add(standup_config)

        # Create feedback config (Friday vibe checks)
        feedback_config = FeedbackConfig(
            client_id=client_id,
            schedule_time=dt_time(15, 0),  # 3 PM default
            is_enabled=vibe_check_enabled
        )
        session.add(feedback_config)

        # Flush to ensure all objects have IDs
        session.flush()

        logger.info(f"Added client: {slack_user_id} (ID: {client_id})")

    # Transaction committed - now schedule jobs outside the transaction
    # Use a fresh session kept open during scheduling so lazy-loaded
    # relationships (e.g. standup_config.client) remain accessible
    try:
        from sqlalchemy.orm import joinedload
        session = get_session()
        try:
            fresh_client = session.query(Client).options(
                joinedload(Client.standup_config),
                joinedload(Client.feedback_config)
            ).filter_by(id=client_id).first()
            if fresh_client and fresh_client.standup_config:
                add_standup_job(fresh_client.standup_config)
            if vibe_check_enabled and fresh_client and fresh_client.feedback_config:
                add_feedback_job(fresh_client.feedback_config)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Failed to schedule jobs for client {client_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Jobs failed but client was created - log and continue

    return {"id": client_id, "slack_user_id": slack_user_id, "display_name": display_name}


def get_client(client_id: int) -> Optional[Client]:
    """Get client by ID"""
    from sqlalchemy.orm import joinedload
    session = get_session()
    try:
        client = session.query(Client).options(
            joinedload(Client.standup_config),
            joinedload(Client.feedback_config)
        ).filter_by(id=client_id).first()
        if client:
            session.expunge(client)
        return client
    finally:
        session.close()


def get_client_by_slack_id(workspace_id: int, slack_user_id: str) -> Optional[Client]:
    """Get client by Slack user ID"""
    from sqlalchemy.orm import joinedload
    session = get_session()
    try:
        client = session.query(Client).options(
            joinedload(Client.standup_config),
            joinedload(Client.feedback_config)
        ).filter_by(
            workspace_id=workspace_id,
            slack_user_id=slack_user_id
        ).first()
        if client:
            session.expunge(client)
        return client
    finally:
        session.close()


def get_workspace_clients(workspace_id: int, active_only: bool = True) -> List[Client]:
    """Get all clients for a workspace"""
    from sqlalchemy.orm import joinedload
    session = get_session()
    try:
        query = session.query(Client).options(
            joinedload(Client.standup_config),
            joinedload(Client.feedback_config)
        ).filter_by(workspace_id=workspace_id)
        if active_only:
            query = query.filter_by(is_active=True)
        clients = query.all()
        for client in clients:
            session.expunge(client)
        return clients
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
