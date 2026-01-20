"""Authentication middleware"""

from functools import wraps
from src.services.workspace_service import is_workspace_admin, get_workspace_by_team_id
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def require_admin(func):
    """
    Decorator to require admin authorization for commands.

    Handles both slash commands and modal/view submissions which have
    different body structures.

    Usage:
        @app.command("/vibe-add-client")
        @require_admin
        def handle_add_client(ack, command, client, body):
            ...
    """
    @wraps(func)
    def wrapper(ack, *args, **kwargs):
        # IMPORTANT: Acknowledge immediately to prevent Slack timeout
        # Slack requires ack() within 3 seconds
        ack()

        # Get body and command from kwargs (Slack Bolt passes these)
        body = kwargs.get('body', {})
        command = kwargs.get('command', {})
        slack_client = kwargs.get('client')

        # Determine team_id and user_id based on request type
        # Slash commands have team_id at top level
        # Modal submissions have team.id nested
        if 'team_id' in body:
            # Slash command
            team_id = body.get('team_id')
            user_id = body.get('user_id')
            channel_id = body.get('channel_id', user_id)
        elif 'team_id' in command:
            # Slash command via command dict
            team_id = command.get('team_id')
            user_id = command.get('user_id')
            channel_id = command.get('channel_id', user_id)
        elif 'team' in body:
            # Modal/view submission
            team_id = body.get('team', {}).get('id')
            user_id = body.get('user', {}).get('id')
            channel_id = user_id
        else:
            # Fallback - try to extract from any available source
            team_id = body.get('team_id') or command.get('team_id')
            user_id = body.get('user_id') or command.get('user_id')
            channel_id = body.get('channel_id') or command.get('channel_id') or user_id

        if not team_id or not user_id:
            logger.error("Could not extract team_id or user_id from request")
            return

        try:
            workspace = get_workspace_by_team_id(team_id)

            if not workspace or not is_workspace_admin(workspace.id, user_id):
                if slack_client:
                    try:
                        # For DM channels, send a regular message instead of ephemeral
                        # chat_postEphemeral doesn't work in DMs
                        if channel_id and channel_id.startswith('D'):
                            slack_client.chat_postMessage(
                                channel=user_id,
                                text="⛔ You don't have permission to use this command. Only workspace admins can manage Vibe Check.\n\nContact your workspace admin to be added as an admin."
                            )
                        else:
                            slack_client.chat_postEphemeral(
                                channel=channel_id,
                                user=user_id,
                                text="⛔ You don't have permission to use this command. Only workspace admins can manage Vibe Check.\n\nContact your workspace admin to be added as an admin."
                            )
                    except Exception as e:
                        logger.error(f"Failed to send unauthorized message: {e}")
                logger.warning(f"Unauthorized command access attempt by user {user_id} in team {team_id}")
                return

            # User is authorized - call the wrapped function
            # Pass a no-op ack since we already acked
            return func(lambda: None, *args, **kwargs)

        except Exception as e:
            logger.error(f"Error in require_admin middleware: {e}")
            if slack_client and user_id:
                try:
                    slack_client.chat_postMessage(
                        channel=user_id,
                        text="⚠️ An error occurred. Please try again."
                    )
                except:
                    pass

    return wrapper
