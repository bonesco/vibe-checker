"""View submission handlers for modals"""

from datetime import time as dt_time
from src.services.client_service import (
    add_client,
    get_client,
    pause_client_standups,
    resume_client_standups,
    remove_client
)
from src.services.workspace_service import get_workspace_by_team_id, set_vibe_check_channel
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def register(app):
    """Register all view submission handlers"""

    @app.view("add_client_modal")
    def handle_add_client_submission(ack, body, client, view):
        """Handle add client modal submission"""
        ack()
        try:
            # Extract form values
            values = view["state"]["values"]

            user_id = values["user_select"]["user_input"]["selected_user"]
            timezone = values["timezone"]["timezone_select"]["selected_option"]["value"]
            schedule_type = values["schedule_type"]["schedule_type_select"]["selected_option"]["value"]
            time_str = values["standup_time"]["time_select"]["selected_time"]

            # Parse time
            hour, minute = map(int, time_str.split(":"))
            schedule_time = dt_time(hour=hour, minute=minute)

            # Get workspace
            workspace = get_workspace_by_team_id(body["team"]["id"])

            # Get user info from Slack
            user_info = client.users_info(user=user_id)
            display_name = user_info["user"]["real_name"]
            email = user_info["user"]["profile"].get("email")

            # Add client
            new_client = add_client(
                workspace_id=workspace.id,
                slack_user_id=user_id,
                display_name=display_name,
                email=email,
                timezone=timezone,
                schedule_type=schedule_type,
                schedule_time=schedule_time
            )

            # Send confirmation
            client.chat_postMessage(
                channel=body["user"]["id"],
                text=f"✅ Successfully added <@{user_id}> as a client!\n"
                     f"• Schedule: {schedule_type} at {schedule_time.strftime('%I:%M %p')}\n"
                     f"• Timezone: {timezone}"
            )

            logger.info(f"Added new client via modal: {user_id} (ID: {new_client.id})")

        except Exception as e:
            logger.error(f"Error handling add client submission: {e}")

    @app.view("pause_client_modal")
    def handle_pause_client_submission(ack, body, client, view):
        """Handle pause client modal submission"""
        ack()
        try:
            # Extract selected client ID
            values = view["state"]["values"]
            client_id = int(values["client_select"]["client_select_input"]["selected_option"]["value"])

            # Get client info for message
            client_obj = get_client(client_id)
            client_name = client_obj.display_name if client_obj else f"Client {client_id}"

            # Pause the client
            success = pause_client_standups(client_id)

            if success:
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"⏸️ Standups paused for *{client_name}*.\n"
                         f"Use `/vibe-resume` to resume their standups."
                )
                logger.info(f"Paused standups for client {client_id}")
            else:
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"Failed to pause standups for {client_name}. Please try again."
                )

        except Exception as e:
            logger.error(f"Error handling pause client submission: {e}")

    @app.view("resume_client_modal")
    def handle_resume_client_submission(ack, body, client, view):
        """Handle resume client modal submission"""
        ack()
        try:
            # Extract selected client ID
            values = view["state"]["values"]
            client_id = int(values["client_select"]["client_select_input"]["selected_option"]["value"])

            # Get client info for message
            client_obj = get_client(client_id)
            client_name = client_obj.display_name if client_obj else f"Client {client_id}"

            # Resume the client
            success = resume_client_standups(client_id)

            if success:
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"▶️ Standups resumed for *{client_name}*.\n"
                         f"They will receive standups at their scheduled time."
                )
                logger.info(f"Resumed standups for client {client_id}")
            else:
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"Failed to resume standups for {client_name}. Please try again."
                )

        except Exception as e:
            logger.error(f"Error handling resume client submission: {e}")

    @app.view("remove_client_modal")
    def handle_remove_client_submission(ack, body, client, view):
        """Handle remove client modal submission"""
        ack()
        try:
            # Extract selected client ID
            values = view["state"]["values"]
            client_id = int(values["client_select"]["client_select_input"]["selected_option"]["value"])

            # Get client info for message before removing
            client_obj = get_client(client_id)
            client_name = client_obj.display_name if client_obj else f"Client {client_id}"

            # Remove the client
            success = remove_client(client_id)

            if success:
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"🗑️ *{client_name}* has been removed.\n"
                         f"All their response history has been deleted."
                )
                logger.info(f"Removed client {client_id}")
            else:
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"Failed to remove {client_name}. Please try again."
                )

        except Exception as e:
            logger.error(f"Error handling remove client submission: {e}")

    @app.view("set_channel_modal")
    def handle_set_channel_submission(ack, body, client, view):
        """Handle set vibe channel modal submission"""
        ack()
        try:
            # Extract selected channel
            values = view["state"]["values"]
            channel_id = values["channel_select"]["channel_select_input"]["selected_channel"]

            # Get workspace
            workspace = get_workspace_by_team_id(body["team"]["id"])

            # Update workspace with new channel
            success = set_vibe_check_channel(workspace.id, channel_id)

            if success:
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"✅ Vibe check channel set to <#{channel_id}>.\n"
                         f"Client feedback will be posted there."
                )
                logger.info(f"Set vibe channel to {channel_id} for workspace {workspace.id}")
            else:
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text="Failed to set vibe check channel. Please try again."
                )

        except Exception as e:
            logger.error(f"Error handling set channel submission: {e}")

    logger.info("View handlers registered")
