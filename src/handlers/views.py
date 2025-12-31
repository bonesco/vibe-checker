"""View submission handlers for modals"""

from datetime import time as dt_time
from src.services.client_service import add_client
from src.services.workspace_service import get_workspace_by_team_id
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

    logger.info("View handlers registered")
