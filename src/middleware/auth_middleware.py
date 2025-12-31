"""Authentication middleware"""

from functools import wraps
from src.services.workspace_service import is_workspace_admin, get_workspace_by_team_id
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def require_admin(func):
    """
    Decorator to require admin authorization for commands

    Usage:
        @require_admin
        def my_command_handler(ack, body, client):
            ...
    """
    @wraps(func)
    def wrapper(ack, body, client, *args, **kwargs):
        workspace = get_workspace_by_team_id(body["team"]["id"])
        user_id = body["user"]["id"]

        if not workspace or not is_workspace_admin(workspace.id, user_id):
            ack()
            client.chat_postEphemeral(
                channel=body.get("channel_id", user_id),
                user=user_id,
                text="⛔ You don't have permission to use this command. Only workspace admins can manage Vibe Check."
            )
            logger.warning(f"Unauthorized command access attempt by user {user_id}")
            return

        return func(ack, body, client, *args, **kwargs)

    return wrapper
