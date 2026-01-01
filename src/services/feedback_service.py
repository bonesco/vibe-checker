"""Feedback service for sending and processing weekly feedback"""

from datetime import date, datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from src.models.client import Client
from src.models.feedback_response import FeedbackResponse
from src.services.workspace_service import get_bot_token, get_workspace_by_id
from src.blocks.feedback_blocks import get_feedback_message_blocks, get_feedback_confirmation_blocks, get_vibe_channel_feedback_blocks
from src.database.session import get_session, db_transaction
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def send_feedback_dm(workspace_id: int, client_id: int):
    """
    Send weekly feedback DM to a client

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

        # Use Friday's date as week_ending
        today = date.today()
        week_ending = today

        # Check if already sent this week
        existing = session.query(FeedbackResponse).filter_by(
            client_id=client_id,
            week_ending=week_ending
        ).first()

        if existing:
            logger.info(f"Feedback already sent to client {client_id} this week")
            return

        # Create Slack client and send message
        slack_client = WebClient(token=bot_token)
        blocks = get_feedback_message_blocks(client_id, week_ending)

        response = slack_client.chat_postMessage(
            channel=client.slack_user_id,
            text="Time for your weekly vibe check!",
            blocks=blocks
        )

        logger.info(f"Sent feedback to {client.slack_user_id} (client_id={client_id}, message_ts={response['ts']})")

    except SlackApiError as e:
        logger.error(f"Slack API error sending feedback: {e.response['error']}")
    except Exception as e:
        logger.error(f"Failed to send feedback: {e}")
    finally:
        session.close()


def save_feedback_response(
    client_id: int,
    workspace_id: int,
    week_ending: date,
    feeling_rating: int,
    feeling_text: str,
    improvements: str,
    blockers: str,
    satisfaction_rating: int,
    message_ts: str,
    start_time: datetime = None  # Deprecated - now calculated from message_ts
) -> FeedbackResponse:
    """
    Save feedback response and post to vibe check channel

    Args:
        client_id: Client database ID
        workspace_id: Workspace database ID
        week_ending: Friday date
        feeling_rating: 1-5 feeling rating
        feeling_text: Additional thoughts
        improvements: Improvement suggestions
        blockers: Any blockers
        satisfaction_rating: 1-5 satisfaction rating
        message_ts: Original message timestamp (used to calculate response time)
        start_time: Deprecated - kept for compatibility

    Returns:
        Created FeedbackResponse
    """
    with db_transaction() as session:
        # Calculate response time from Slack message timestamp
        # message_ts format is "1234567890.123456" (Unix timestamp)
        try:
            message_sent_time = datetime.utcfromtimestamp(float(message_ts))
            response_time = int((datetime.utcnow() - message_sent_time).total_seconds())
        except (ValueError, TypeError):
            logger.warning(f"Could not parse message_ts: {message_ts}, using 0 for response time")
            response_time = 0

        # Create response
        response = FeedbackResponse(
            client_id=client_id,
            workspace_id=workspace_id,
            week_ending=week_ending,
            feeling_rating=feeling_rating,
            feeling_text=feeling_text,
            improvements=improvements,
            blockers=blockers,
            satisfaction_rating=satisfaction_rating,
            message_ts=message_ts,
            response_time_seconds=response_time
        )
        session.add(response)
        session.flush()

        # Get client for posting to vibe channel
        client = session.query(Client).filter_by(id=client_id).first()

        logger.info(f"Saved feedback response for client {client_id} week ending {week_ending}")

    # Post to vibe channel (outside transaction)
    post_feedback_to_vibe_channel(workspace_id, client, response)

    return response


def post_feedback_to_vibe_channel(workspace_id: int, client: Client, response: FeedbackResponse):
    """
    Post formatted feedback to the vibe check channel

    Args:
        workspace_id: Workspace database ID
        client: Client who submitted feedback
        response: FeedbackResponse data
    """
    try:
        workspace = get_workspace_by_id(workspace_id)
        if not workspace or not workspace.vibe_check_channel_id:
            logger.warning(f"No vibe check channel configured for workspace {workspace_id}")
            return

        bot_token = get_bot_token(workspace_id)
        if not bot_token:
            return

        slack_client = WebClient(token=bot_token)
        blocks = get_vibe_channel_feedback_blocks(client, response)

        result = slack_client.chat_postMessage(
            channel=workspace.vibe_check_channel_id,
            text=f"Weekly feedback from {client.display_name or client.slack_user_id}",
            blocks=blocks
        )

        # Update response with vibe channel message timestamp
        with db_transaction() as session:
            db_response = session.query(FeedbackResponse).filter_by(id=response.id).first()
            if db_response:
                db_response.vibe_channel_message_ts = result['ts']

        logger.info(f"Posted feedback to vibe channel for client {client.id}")

    except SlackApiError as e:
        logger.error(f"Failed to post to vibe channel: {e.response['error']}")
    except Exception as e:
        logger.error(f"Error posting to vibe channel: {e}")
