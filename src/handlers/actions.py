"""Action handlers for Block Kit interactions"""

from datetime import datetime, date
from src.blocks.standup_blocks import get_standup_confirmation_blocks
from src.blocks.feedback_blocks import get_feedback_confirmation_blocks
from src.services.standup_service import save_standup_response
from src.services.feedback_service import save_feedback_response
from src.services.workspace_service import get_workspace_by_team_id
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def register(app):
    """Register all action handlers"""

    @app.action("submit_standup")
    def handle_standup_submission(ack, body, client, action):
        """Handle standup submission button click"""
        ack()
        try:
            # Parse client_id and date from action value
            client_id, date_str = action["value"].split("|")
            client_id = int(client_id)
            scheduled_date = date.fromisoformat(date_str)

            # Extract form values from Block Kit state
            state_values = body["state"]["values"]

            # Extract input values using block_id and action_id
            accomplishments = state_values.get(f"accomplishments_{client_id}_{date_str}", {}).get("accomplishments_input", {}).get("value", "")
            working_on = state_values.get(f"working_on_{client_id}_{date_str}", {}).get("working_on_input", {}).get("value", "")
            blockers = state_values.get(f"blockers_{client_id}_{date_str}", {}).get("blockers_input", {}).get("value", "")

            # Get workspace
            workspace = get_workspace_by_team_id(body["team"]["id"])

            # Save response
            save_standup_response(
                client_id=client_id,
                workspace_id=workspace.id,
                scheduled_date=scheduled_date,
                accomplishments=accomplishments,
                working_on=working_on,
                blockers=blockers,
                message_ts=body["message"]["ts"],
                start_time=datetime.utcnow()  # Should track actual send time
            )

            # Update message to show confirmation
            client.chat_update(
                channel=body["channel"]["id"],
                ts=body["message"]["ts"],
                text="Standup submitted!",
                blocks=get_standup_confirmation_blocks(submitted=True)
            )

            logger.info(f"Standup submitted by client {client_id}")

        except Exception as e:
            logger.error(f"Error handling standup submission: {e}")

    @app.action("skip_standup")
    def handle_standup_skip(ack, body, client):
        """Handle standup skip button click"""
        ack()
        try:
            # Update message to show skip confirmation
            client.chat_update(
                channel=body["channel"]["id"],
                ts=body["message"]["ts"],
                text="Standup skipped",
                blocks=get_standup_confirmation_blocks(submitted=False)
            )

            logger.info("Standup skipped")

        except Exception as e:
            logger.error(f"Error handling standup skip: {e}")

    @app.action("submit_feedback")
    def handle_feedback_submission(ack, body, client, action):
        """Handle feedback submission button click"""
        ack()
        try:
            # Parse client_id and week_ending from action value
            client_id, week_str = action["value"].split("|")
            client_id = int(client_id)
            week_ending = date.fromisoformat(week_str)

            # Get workspace
            workspace = get_workspace_by_team_id(body["team"]["id"])

            # Extract form values from Block Kit state
            state_values = body["state"]["values"]

            # Extract ratings from dropdowns
            feeling_rating_block = state_values.get(f"feeling_rating_{client_id}_{week_str}", {})
            feeling_rating = int(feeling_rating_block.get("feeling_rating_select", {}).get("selected_option", {}).get("value", "3"))

            satisfaction_rating_block = state_values.get(f"satisfaction_rating_{client_id}_{week_str}", {})
            satisfaction_rating = int(satisfaction_rating_block.get("satisfaction_rating_select", {}).get("selected_option", {}).get("value", "3"))

            # Extract text inputs
            feeling_text = state_values.get(f"feeling_text_{client_id}_{week_str}", {}).get("feeling_text_input", {}).get("value", "")
            improvements = state_values.get(f"improvements_{client_id}_{week_str}", {}).get("improvements_input", {}).get("value", "")
            blockers = state_values.get(f"blockers_{client_id}_{week_str}", {}).get("blockers_input", {}).get("value", "")

            # Save response and post to vibe channel
            save_feedback_response(
                client_id=client_id,
                workspace_id=workspace.id,
                week_ending=week_ending,
                feeling_rating=feeling_rating,
                feeling_text=feeling_text,
                improvements=improvements,
                blockers=blockers,
                satisfaction_rating=satisfaction_rating,
                message_ts=body["message"]["ts"],
                start_time=datetime.utcnow()
            )

            # Update message to show confirmation
            client.chat_update(
                channel=body["channel"]["id"],
                ts=body["message"]["ts"],
                text="Feedback submitted!",
                blocks=get_feedback_confirmation_blocks()
            )

            logger.info(f"Feedback submitted by client {client_id}")

        except Exception as e:
            logger.error(f"Error handling feedback submission: {e}")

    # Handle dropdown selections (they don't need immediate response, just state updates)
    @app.action("feeling_rating_select")
    @app.action("satisfaction_rating_select")
    def handle_rating_select(ack):
        """Acknowledge rating selections"""
        ack()

    logger.info("Action handlers registered")
