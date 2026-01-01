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
            state_values = body.get("state", {}).get("values", {})

            # Debug logging to help diagnose state extraction issues
            logger.debug(f"Standup submission - client_id={client_id}, date={date_str}")
            logger.debug(f"State values keys: {list(state_values.keys())}")

            # Extract input values using block_id and action_id
            accomplishments_block = state_values.get(f"accomplishments_{client_id}_{date_str}", {})
            working_on_block = state_values.get(f"working_on_{client_id}_{date_str}", {})
            blockers_block = state_values.get(f"blockers_{client_id}_{date_str}", {})

            accomplishments = accomplishments_block.get("accomplishments_input", {}).get("value", "")
            working_on = working_on_block.get("working_on_input", {}).get("value", "")
            blockers = blockers_block.get("blockers_input", {}).get("value", "")

            # Check if this is a test submission (client_id=-1)
            if client_id == -1:
                logger.info("Test standup submission received - skipping database save")
                client.chat_update(
                    channel=body["channel"]["id"],
                    ts=body["message"]["ts"],
                    text="Test standup submitted!",
                    blocks=get_standup_confirmation_blocks(submitted=True)
                )
                return

            # Warn if state extraction might have failed
            if not accomplishments and not working_on:
                logger.warning(f"Empty standup values extracted - state keys: {list(state_values.keys())}")

            # Get workspace
            workspace = get_workspace_by_team_id(body["team"]["id"])
            if not workspace:
                logger.error(f"Workspace not found for team {body['team']['id']}")
                return

            # Save response
            save_standup_response(
                client_id=client_id,
                workspace_id=workspace.id,
                scheduled_date=scheduled_date,
                accomplishments=accomplishments,
                working_on=working_on,
                blockers=blockers,
                message_ts=body["message"]["ts"],
                start_time=datetime.utcnow()
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
            logger.error(f"Error handling standup submission: {e}", exc_info=True)

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

            # Extract form values from Block Kit state
            state_values = body.get("state", {}).get("values", {})

            # Debug logging to help diagnose state extraction issues
            logger.debug(f"Feedback submission - client_id={client_id}, week={week_str}")
            logger.debug(f"State values keys: {list(state_values.keys())}")

            # Extract ratings from dropdowns (default to 3 if not selected)
            feeling_rating_block = state_values.get(f"feeling_rating_{client_id}_{week_str}", {})
            feeling_select = feeling_rating_block.get("feeling_rating_select", {})
            selected_feeling = feeling_select.get("selected_option")
            feeling_rating = int(selected_feeling.get("value", "3")) if selected_feeling else 3

            satisfaction_rating_block = state_values.get(f"satisfaction_rating_{client_id}_{week_str}", {})
            satisfaction_select = satisfaction_rating_block.get("satisfaction_rating_select", {})
            selected_satisfaction = satisfaction_select.get("selected_option")
            satisfaction_rating = int(selected_satisfaction.get("value", "3")) if selected_satisfaction else 3

            # Extract text inputs
            feeling_text = state_values.get(f"feeling_text_{client_id}_{week_str}", {}).get("feeling_text_input", {}).get("value", "")
            improvements = state_values.get(f"improvements_{client_id}_{week_str}", {}).get("improvements_input", {}).get("value", "")
            blockers = state_values.get(f"blockers_{client_id}_{week_str}", {}).get("blockers_input", {}).get("value", "")

            # Check if this is a test submission (client_id=-1)
            if client_id == -1:
                logger.info("Test feedback submission received - skipping database save")
                client.chat_update(
                    channel=body["channel"]["id"],
                    ts=body["message"]["ts"],
                    text="Test feedback submitted!",
                    blocks=get_feedback_confirmation_blocks()
                )
                return

            # Get workspace
            workspace = get_workspace_by_team_id(body["team"]["id"])
            if not workspace:
                logger.error(f"Workspace not found for team {body['team']['id']}")
                return

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
            logger.error(f"Error handling feedback submission: {e}", exc_info=True)

    # Handle dropdown selections (they don't need immediate response, just state updates)
    @app.action("feeling_rating_select")
    @app.action("satisfaction_rating_select")
    def handle_rating_select(ack):
        """Acknowledge rating selections"""
        ack()

    logger.info("Action handlers registered")
