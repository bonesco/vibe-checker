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
    def handle_list_clients(ack, body, respond):
        """List all clients"""
        ack()
        try:
            workspace = get_workspace_by_team_id(body["team_id"])
            if not workspace:
                respond(text="Workspace not found")
                return

            clients = get_workspace_clients(workspace.id)
            blocks = get_client_list_blocks(clients)

            respond(
                text=f"Found {len(clients)} clients",
                blocks=blocks
            )
        except Exception as e:
            logger.error(f"Error listing clients: {e}")
            respond(text="An error occurred. Please try again.")

    @app.command("/vibe-help")
    def handle_help(ack, respond):
        """Show help documentation"""
        ack()
        try:
            blocks = get_help_blocks()
            respond(
                text="Vibe Check Help",
                blocks=blocks
            )
        except Exception as e:
            logger.error(f"Error showing help: {e}")
            respond(text="An error occurred. Please try again.")

    @app.command("/vibe-test")
    def handle_test(ack, command, client, respond):
        """Send a test standup to the admin (uses client_id=-1 for test mode)"""
        ack()
        try:
            from datetime import date
            from src.blocks.standup_blocks import get_standup_message_blocks

            # Use client_id=-1 as a sentinel value for test mode
            # The action handler will recognize this and skip database save
            blocks = get_standup_message_blocks(-1, date.today())

            client.chat_postMessage(
                channel=command["user_id"],
                text="Test standup message",
                blocks=blocks
            )

            respond(text="✅ Test standup sent to your DMs! (This is a test - responses won't be saved)")
        except Exception as e:
            logger.error(f"Error sending test: {e}")
            respond(text="An error occurred. Please try again.")

    @app.command("/vibe-test-feedback")
    def handle_test_feedback(ack, command, client, respond):
        """Send a test feedback form to the admin (uses client_id=-1 for test mode)"""
        ack()
        try:
            from datetime import date
            from src.blocks.feedback_blocks import get_feedback_message_blocks

            # Use client_id=-1 as a sentinel value for test mode
            # The action handler will recognize this and skip database save
            blocks = get_feedback_message_blocks(-1, date.today())

            client.chat_postMessage(
                channel=command["user_id"],
                text="Test weekly vibe check",
                blocks=blocks
            )

            respond(text="✅ Test feedback form sent to your DMs! (This is a test - responses won't be saved)")
        except Exception as e:
            logger.error(f"Error sending test feedback: {e}")
            respond(text="An error occurred. Please try again.")

    @app.command("/vibe-pause")
    def handle_pause_client(ack, command, client, body, respond):
        """Open modal to pause a client's standups"""
        ack()
        try:
            workspace = get_workspace_by_team_id(body["team_id"])
            if not workspace:
                respond(text="Workspace not found. Please reinstall the app.")
                return

            clients = get_workspace_clients(workspace.id)
            modal = get_pause_client_modal(clients)

            if modal:
                client.views_open(
                    trigger_id=command["trigger_id"],
                    view=modal
                )
            else:
                respond(
                    text="No active clients to pause.",
                    blocks=get_no_clients_message("pause")
                )
        except Exception as e:
            logger.error(f"Error opening pause modal: {e}")
            respond(text="An error occurred. Please try again.")

    @app.command("/vibe-resume")
    def handle_resume_client(ack, command, client, body, respond):
        """Open modal to resume a client's standups"""
        ack()
        try:
            workspace = get_workspace_by_team_id(body["team_id"])
            if not workspace:
                respond(text="Workspace not found. Please reinstall the app.")
                return

            clients = get_workspace_clients(workspace.id)
            modal = get_resume_client_modal(clients)

            if modal:
                client.views_open(
                    trigger_id=command["trigger_id"],
                    view=modal
                )
            else:
                respond(
                    text="No paused clients to resume.",
                    blocks=get_no_clients_message("resume")
                )
        except Exception as e:
            logger.error(f"Error opening resume modal: {e}")
            respond(text="An error occurred. Please try again.")

    @app.command("/vibe-remove-client")
    def handle_remove_client(ack, command, client, body, respond):
        """Open modal to remove a client"""
        ack()
        try:
            workspace = get_workspace_by_team_id(body["team_id"])
            if not workspace:
                respond(text="Workspace not found. Please reinstall the app.")
                return

            clients = get_workspace_clients(workspace.id)
            modal = get_remove_client_modal(clients)

            if modal:
                client.views_open(
                    trigger_id=command["trigger_id"],
                    view=modal
                )
            else:
                respond(
                    text="No clients to remove.",
                    blocks=get_no_clients_message("remove")
                )
        except Exception as e:
            logger.error(f"Error opening remove modal: {e}")
            respond(text="An error occurred. Please try again.")

    @app.command("/vibe-set-channel")
    def handle_set_channel(ack, command, client, respond):
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
            respond(text="An error occurred. Please try again.")

    logger.info("Command handlers registered")
