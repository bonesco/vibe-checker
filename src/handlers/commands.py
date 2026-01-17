"""Slash command handlers"""

from src.blocks.admin_blocks import (
    get_add_client_modal,
    get_client_list_blocks,
    get_help_blocks,
    get_pause_client_modal,
    get_resume_client_modal,
    get_remove_client_modal,
    get_set_channel_modal,
    get_no_clients_message
)
from src.services.client_service import get_workspace_clients
from src.services.workspace_service import get_workspace_by_team_id, add_admin, is_workspace_admin
from src.middleware.auth_middleware import require_admin
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def register(app):
    """Register all slash command handlers"""

    @app.command("/vibe-add-client")
    @require_admin
    def handle_add_client(ack, command, client, body):
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
    @require_admin
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
    def handle_help(ack, command, client, body):
        """Show help documentation - available to all users"""
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
    @require_admin
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
                text="Test standup sent to your DMs!"
            )
        except Exception as e:
            logger.error(f"Error sending test: {e}")

    @app.command("/vibe-pause")
    @require_admin
    def handle_pause_client(ack, command, client, body):
        """Open modal to pause a client's standups"""
        ack()
        try:
            workspace = get_workspace_by_team_id(body["team_id"])
            if not workspace:
                client.chat_postEphemeral(
                    channel=command["channel_id"],
                    user=command["user_id"],
                    text="Workspace not found. Please reinstall the app."
                )
                return

            clients = get_workspace_clients(workspace.id)
            modal = get_pause_client_modal(clients)

            if modal:
                client.views_open(
                    trigger_id=command["trigger_id"],
                    view=modal
                )
            else:
                client.chat_postEphemeral(
                    channel=command["channel_id"],
                    user=command["user_id"],
                    text="No active clients to pause.",
                    blocks=get_no_clients_message("pause")
                )
        except Exception as e:
            logger.error(f"Error opening pause modal: {e}")

    @app.command("/vibe-resume")
    @require_admin
    def handle_resume_client(ack, command, client, body):
        """Open modal to resume a client's standups"""
        ack()
        try:
            workspace = get_workspace_by_team_id(body["team_id"])
            if not workspace:
                client.chat_postEphemeral(
                    channel=command["channel_id"],
                    user=command["user_id"],
                    text="Workspace not found. Please reinstall the app."
                )
                return

            clients = get_workspace_clients(workspace.id)
            modal = get_resume_client_modal(clients)

            if modal:
                client.views_open(
                    trigger_id=command["trigger_id"],
                    view=modal
                )
            else:
                client.chat_postEphemeral(
                    channel=command["channel_id"],
                    user=command["user_id"],
                    text="No paused clients to resume.",
                    blocks=get_no_clients_message("resume")
                )
        except Exception as e:
            logger.error(f"Error opening resume modal: {e}")

    @app.command("/vibe-remove-client")
    @require_admin
    def handle_remove_client(ack, command, client, body):
        """Open modal to remove a client"""
        ack()
        try:
            workspace = get_workspace_by_team_id(body["team_id"])
            if not workspace:
                client.chat_postEphemeral(
                    channel=command["channel_id"],
                    user=command["user_id"],
                    text="Workspace not found. Please reinstall the app."
                )
                return

            clients = get_workspace_clients(workspace.id)
            modal = get_remove_client_modal(clients)

            if modal:
                client.views_open(
                    trigger_id=command["trigger_id"],
                    view=modal
                )
            else:
                client.chat_postEphemeral(
                    channel=command["channel_id"],
                    user=command["user_id"],
                    text="No clients to remove.",
                    blocks=get_no_clients_message("remove")
                )
        except Exception as e:
            logger.error(f"Error opening remove modal: {e}")

    @app.command("/vibe-set-channel")
    @require_admin
    def handle_set_channel(ack, command, client, body):
        """Open modal to set the vibe check channel"""
        ack()
        try:
            modal = get_set_channel_modal()
            client.views_open(
                trigger_id=command["trigger_id"],
                view=modal
            )
        except Exception as e:
            logger.error(f"Error opening set channel modal: {e}")

    @app.command("/vibe-admin")
    @require_admin
    def handle_admin(ack, command, client, body):
        """Manage workspace admins"""
        ack()
        try:
            workspace = get_workspace_by_team_id(body["team_id"])
            if not workspace:
                client.chat_postEphemeral(
                    channel=command["channel_id"],
                    user=command["user_id"],
                    text="Workspace not found."
                )
                return

            # Check for user mention in command text
            text = command.get("text", "").strip()

            if text.startswith("add "):
                # Extract user ID from mention (format: <@U12345|username> or <@U12345>)
                import re
                match = re.search(r'<@(U[A-Z0-9]+)(?:\|[^>]+)?>', text)
                if match:
                    new_admin_id = match.group(1)
                    if add_admin(workspace.id, new_admin_id):
                        client.chat_postEphemeral(
                            channel=command["channel_id"],
                            user=command["user_id"],
                            text=f"Added <@{new_admin_id}> as an admin."
                        )
                    else:
                        client.chat_postEphemeral(
                            channel=command["channel_id"],
                            user=command["user_id"],
                            text="Failed to add admin. Please try again."
                        )
                else:
                    client.chat_postEphemeral(
                        channel=command["channel_id"],
                        user=command["user_id"],
                        text="Please mention a user to add. Usage: `/vibe-admin add @username`"
                    )
            else:
                # Show current admins and usage
                admin_ids = workspace.admin_user_ids or []
                admin_list = "\n".join([f"  - <@{uid}>" for uid in admin_ids]) if admin_ids else "  (none)"

                client.chat_postEphemeral(
                    channel=command["channel_id"],
                    user=command["user_id"],
                    blocks=[
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": "Vibe Check Admin Management"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Current Admins:*\n{admin_list}"
                            }
                        },
                        {
                            "type": "divider"
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "*Usage:*\n`/vibe-admin` - Show current admins\n`/vibe-admin add @user` - Add a new admin"
                            }
                        }
                    ],
                    text="Vibe Check Admin Management"
                )
        except Exception as e:
            logger.error(f"Error in admin command: {e}")

    logger.info("Command handlers registered")
