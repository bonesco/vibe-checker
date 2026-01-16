"""Authentication middleware"""

from functools import wraps
from src.services.workspace_service import is_workspace_admin, get_workspace_by_team_id
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def _get_team_id(body):
    """Extract team ID from body (handles both command and event/action formats)"""
    if "team_id" in body:
        return body["team_id"]
    if "team" in body and isinstance(body["team"], dict):
        return body["team"].get("id")
    return None


def _get_user_id(body):
    """Extract user ID from body (handles both command and event/action formats)"""
    if "user_id" in body:
        return body["user_id"]
    if "user" in body and isinstance(body["user"], dict):
        return body["user"].get("id")
    if "user" in body and isinstance(body["user"], str):
        return body["user"]
    return None


def _get_channel_id(body):
    """Extract channel ID from body"""
    return body.get("channel_id") or body.get("channel", {}).get("id")


def require_admin(func):
    """
    Decorator to require admin authorization for commands

    Usage:
        @require_admin
        def my_command_handler(ack, body, client, ...):
            ...
    """
    @wraps(func)
    def wrapper(ack, body, client, *args, **kwargs):
        team_id = _get_team_id(body)
        user_id = _get_user_id(body)
        channel_id = _get_channel_id(body)

        workspace = get_workspace_by_team_id(team_id) if team_id else None

        if not workspace or not is_workspace_admin(workspace.id, user_id):
            ack()
            client.chat_postEphemeral(
                channel=channel_id or user_id,
                user=user_id,
                text="You don't have permission to use this command. Only workspace admins can manage Vibe Check."
            )
            logger.warning(f"Unauthorized command access attempt by user {user_id}")
            return

        return func(ack, body, client, *args, **kwargs)

    return wrapper
