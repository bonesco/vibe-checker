"""Workspace management service"""

from typing import Optional, List
from sqlalchemy.orm import Session
from src.models.workspace import Workspace
from src.utils.encryption import encrypt_token, decrypt_token
from src.utils.logger import setup_logger
from src.database.session import get_session, db_transaction

logger = setup_logger(__name__)


def create_workspace(
    team_id: str,
    team_name: str,
    bot_token: str,
    bot_user_id: str,
    scope: str,
    installer_user_id: str
) -> Workspace:
    """
    Create a new workspace after OAuth installation

    Args:
        team_id: Slack team/workspace ID
        team_name: Workspace name
        bot_token: Bot access token
        bot_user_id: Bot user ID
        scope: Granted scopes
        installer_user_id: User who installed the app (becomes first admin)

    Returns:
        Created workspace

    """
    with db_transaction() as session:
        # Check if workspace already exists
        existing = session.query(Workspace).filter_by(team_id=team_id).first()

        if existing:
            # Update existing workspace
            existing.team_name = team_name
            existing.bot_token = encrypt_token(bot_token)
            existing.bot_user_id = bot_user_id
            existing.scope = scope
            existing.is_active = True

            # Add installer as admin if not already
            if installer_user_id not in (existing.admin_user_ids or []):
                existing.admin_user_ids = (existing.admin_user_ids or []) + [installer_user_id]

            logger.info(f"Updated workspace: {team_id}")
            return existing
        else:
            # Create new workspace
            workspace = Workspace(
                team_id=team_id,
                team_name=team_name,
                bot_token=encrypt_token(bot_token),
                bot_user_id=bot_user_id,
                scope=scope,
                is_active=True,
                admin_user_ids=[installer_user_id]
            )
            session.add(workspace)
            logger.info(f"Created new workspace: {team_id}")
            return workspace


def get_workspace_by_team_id(team_id: str) -> Optional[Workspace]:
    """Get workspace by Slack team ID"""
    session = get_session()
    try:
        return session.query(Workspace).filter_by(team_id=team_id).first()
    finally:
        session.close()


def get_workspace_by_id(workspace_id: int) -> Optional[Workspace]:
    """Get workspace by database ID"""
    session = get_session()
    try:
        return session.query(Workspace).filter_by(id=workspace_id).first()
    finally:
        session.close()


def get_bot_token(workspace_id: int) -> Optional[str]:
    """
    Get decrypted bot token for a workspace

    Args:
        workspace_id: Workspace database ID

    Returns:
        Decrypted bot token or None
    """
    workspace = get_workspace_by_id(workspace_id)
    if workspace and workspace.bot_token:
        return decrypt_token(workspace.bot_token)
    return None


def set_vibe_check_channel(workspace_id: int, channel_id: str) -> bool:
    """
    Set the vibe check channel for a workspace

    Args:
        workspace_id: Workspace database ID
        channel_id: Slack channel ID

    Returns:
        True if successful
    """
    try:
        with db_transaction() as session:
            workspace = session.query(Workspace).filter_by(id=workspace_id).first()
            if workspace:
                workspace.vibe_check_channel_id = channel_id
                logger.info(f"Set vibe check channel for workspace {workspace_id}: {channel_id}")
                return True
            return False
    except Exception as e:
        logger.error(f"Failed to set vibe check channel: {e}")
        return False


def add_admin(workspace_id: int, user_id: str) -> bool:
    """Add a user as admin for a workspace"""
    try:
        with db_transaction() as session:
            workspace = session.query(Workspace).filter_by(id=workspace_id).first()
            if workspace:
                if user_id not in (workspace.admin_user_ids or []):
                    workspace.admin_user_ids = (workspace.admin_user_ids or []) + [user_id]
                    logger.info(f"Added admin {user_id} to workspace {workspace_id}")
                return True
            return False
    except Exception as e:
        logger.error(f"Failed to add admin: {e}")
        return False


def is_workspace_admin(workspace_id: int, user_id: str) -> bool:
    """Check if user is an admin for the workspace"""
    workspace = get_workspace_by_id(workspace_id)
    return workspace and workspace.is_admin(user_id)
