"""Slash command handlers"""

from src.blocks.admin_blocks import get_add_client_modal, get_client_list_blocks, get_help_blocks
from src.services.client_service import get_workspace_clients
from src.services.workspace_service import get_workspace_by_team_id
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def register(app):
    """Register all slash command handlers"""

    @app.command("/vibe-add-client")
    def handle_add_client(ack, command, client):
        """Open modal to add a new client"""
        ack()
        try:
            client.views_open(
                trigger_id=command["trigger_id"],
                view=get_add_client_modal()
            )
        except Exception as e:
            logger.error(f"Error opening add client modal: {e}")

    @app.command("/vibe-list-clients")
    def handle_list_clients(ack, command, client, body):
        """List all clients"""
        ack()
        try:
            workspace = get_workspace_by_team_id(body["team_id"])
            if not workspace:
                client.chat_postEphemeral(
                    channel=command["channel_id"],
                    user=command["user_id"],
                    text="Workspace not found"
                )
                return

            clients = get_workspace_clients(workspace.id)
            blocks = get_client_list_blocks(clients)

            client.chat_postEphemeral(
                channel=command["channel_id"],
                user=command["user_id"],
                text=f"Found {len(clients)} clients",
                blocks=blocks
            )
        except Exception as e:
            logger.error(f"Error listing clients: {e}")

    @app.command("/vibe-help")
    def handle_help(ack, command, client):
        """Show help documentation"""
        ack()
        try:
            blocks = get_help_blocks()
            client.chat_postEphemeral(
                channel=command["channel_id"],
                user=command["user_id"],
                text="Vibe Check Help",
                blocks=blocks
            )
        except Exception as e:
            logger.error(f"Error showing help: {e}")

    @app.command("/vibe-test")
    def handle_test(ack, command, client, body):
        """Send a test standup to the admin"""
        ack()
        try:
            from datetime import date
            from src.blocks.standup_blocks import get_standup_message_blocks

            blocks = get_standup_message_blocks(0, date.today())

            client.chat_postMessage(
                channel=command["user_id"],
                text="Test standup message",
                blocks=blocks
            )

            client.chat_postEphemeral(
                channel=command["channel_id"],
                user=command["user_id"],
                text="✅ Test standup sent to your DMs!"
            )
        except Exception as e:
            logger.error(f"Error sending test: {e}")

    logger.info("Command handlers registered")
