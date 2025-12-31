"""Standup service for sending and processing standup messages"""

from datetime import date, datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from src.models.client import Client
from src.models.standup_response import StandupResponse
from src.services.workspace_service import get_bot_token
from src.blocks.standup_blocks import get_standup_message_blocks, get_standup_confirmation_blocks
from src.database.session import get_session, db_transaction
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def send_standup_dm(workspace_id: int, client_id: int):
    """
    Send standup DM to a client

    Args:
        workspace_id: Workspace database ID
        client_id: Client database ID
    """
    session = get_session()
    try:
        # Get client and bot token
        client = session.query(Client).filter_by(id=client_id).first()
        if not client or not client.is_active:
            logger.warning(f"Client {client_id} not found or inactive")
            return

        bot_token = get_bot_token(workspace_id)
        if not bot_token:
            logger.error(f"Bot token not found for workspace {workspace_id}")
            return

        # Check if already sent today
        today = date.today()
        existing = session.query(StandupResponse).filter_by(
            client_id=client_id,
            scheduled_date=today
        ).first()

        if existing:
            logger.info(f"Standup already sent to client {client_id} today")
            return

        # Create Slack client and send message
        slack_client = WebClient(token=bot_token)
        blocks = get_standup_message_blocks(client_id, today)

        response = slack_client.chat_postMessage(
            channel=client.slack_user_id,
            text="Time for your daily standup!",
            blocks=blocks
        )

        logger.info(f"Sent standup to {client.slack_user_id} (client_id={client_id}, message_ts={response['ts']})")

    except SlackApiError as e:
        logger.error(f"Slack API error sending standup: {e.response['error']}")
    except Exception as e:
        logger.error(f"Failed to send standup: {e}")
    finally:
        session.close()


def save_standup_response(
    client_id: int,
    workspace_id: int,
    scheduled_date: date,
    accomplishments: str,
    working_on: str,
    blockers: str,
    message_ts: str,
    start_time: datetime
) -> StandupResponse:
    """
    Save standup response to database

    Args:
        client_id: Client database ID
        workspace_id: Workspace database ID
        scheduled_date: Date of standup
        accomplishments: What was accomplished
        working_on: What they're working on
        blockers: Any blockers
        message_ts: Slack message timestamp
        start_time: When the message was sent

    Returns:
        Created StandupResponse
    """
    with db_transaction() as session:
        response_time = int((datetime.utcnow() - start_time).total_seconds())

        response = StandupResponse(
            client_id=client_id,
            workspace_id=workspace_id,
            scheduled_date=scheduled_date,
            accomplishments=accomplishments,
            working_on=working_on,
            blockers=blockers,
            message_ts=message_ts,
            response_time_seconds=response_time
        )
        session.add(response)

        logger.info(f"Saved standup response for client {client_id} on {scheduled_date}")
        return response
