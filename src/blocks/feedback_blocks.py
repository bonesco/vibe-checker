"""Block Kit templates for weekly feedback messages"""

from datetime import date
from typing import List, Dict, Any
from src.models.feedback_response import FeedbackResponse
from src.models.client import Client


def get_feedback_message_blocks(client_id: int, week_ending: date) -> List[Dict[str, Any]]:
    """
    Create Block Kit blocks for Friday feedback DM

    Args:
        client_id: Client database ID
        week_ending: Friday date this feedback is for

    Returns:
        List of Block Kit blocks
    """
    week_str = week_ending.strftime('%B %d, %Y')
    week_key = week_ending.isoformat()

    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "WEEKLY REVIEW"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "plain_text",
                    "text": f"WEEK ENDING {week_str.upper()}"
                }
            ]
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "block_id": f"feeling_rating_{client_id}_{week_key}",
            "text": {
                "type": "mrkdwn",
                "text": "*How are you feeling about this week?*"
            },
            "accessory": {
                "type": "static_select",
                "action_id": "feeling_rating_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select"
                },
                "options": [
                    {"text": {"type": "plain_text", "text": "5 — Excellent"}, "value": "5"},
                    {"text": {"type": "plain_text", "text": "4 — Good"}, "value": "4"},
                    {"text": {"type": "plain_text", "text": "3 — Neutral"}, "value": "3"},
                    {"text": {"type": "plain_text", "text": "2 — Difficult"}, "value": "2"},
                    {"text": {"type": "plain_text", "text": "1 — Struggling"}, "value": "1"}
                ]
            }
        },
        {
            "type": "input",
            "block_id": f"feeling_text_{client_id}_{week_key}",
            "element": {
                "type": "plain_text_input",
                "action_id": "feeling_text_input",
                "multiline": True,
                "optional": True,
                "placeholder": {
                    "type": "plain_text",
                    "text": "Additional context"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "NOTES"
            },
            "optional": True
        },
        {
            "type": "input",
            "block_id": f"improvements_{client_id}_{week_key}",
            "element": {
                "type": "plain_text_input",
                "action_id": "improvements_input",
                "multiline": True,
                "optional": True,
                "placeholder": {
                    "type": "plain_text",
                    "text": "What could be improved?"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "IMPROVEMENTS"
            },
            "optional": True
        },
        {
            "type": "input",
            "block_id": f"blockers_{client_id}_{week_key}",
            "element": {
                "type": "plain_text_input",
                "action_id": "blockers_input",
                "multiline": True,
                "optional": True,
                "placeholder": {
                    "type": "plain_text",
                    "text": "Any blockers?"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "BLOCKERS"
            },
            "optional": True
        },
        {
            "type": "section",
            "block_id": f"satisfaction_rating_{client_id}_{week_key}",
            "text": {
                "type": "mrkdwn",
                "text": "*Overall satisfaction with our work together:*"
            },
            "accessory": {
                "type": "static_select",
                "action_id": "satisfaction_rating_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Rate"
                },
                "options": [
                    {"text": {"type": "plain_text", "text": "5 — Excellent"}, "value": "5"},
                    {"text": {"type": "plain_text", "text": "4 — Very Good"}, "value": "4"},
                    {"text": {"type": "plain_text", "text": "3 — Good"}, "value": "3"},
                    {"text": {"type": "plain_text", "text": "2 — Fair"}, "value": "2"},
                    {"text": {"type": "plain_text", "text": "1 — Needs Work"}, "value": "1"}
                ]
            }
        },
        {
            "type": "actions",
            "block_id": f"feedback_actions_{client_id}_{week_key}",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Submit"
                    },
                    "style": "primary",
                    "action_id": "submit_feedback",
                    "value": f"{client_id}|{week_key}"
                }
            ]
        }
    ]


def get_feedback_confirmation_blocks() -> List[Dict[str, Any]]:
    """
    Create confirmation message after feedback submission

    Returns:
        List of Block Kit blocks
    """
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*RECEIVED* — Thank you for your feedback."
            }
        }
    ]


def get_vibe_channel_feedback_blocks(client: Client, response: FeedbackResponse) -> List[Dict[str, Any]]:
    """
    Create formatted feedback blocks for posting to vibe check channel

    Args:
        client: Client who submitted feedback
        response: FeedbackResponse with all answers

    Returns:
        List of Block Kit blocks
    """
    # Status indicator based on ratings
    status = "ATTENTION" if response.needs_attention else "OK"
    feeling_score = f"{response.feeling_rating}/5" if response.feeling_rating else "—"
    satisfaction_score = f"{response.satisfaction_rating}/5" if response.satisfaction_rating else "—"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"[{status}] {client.display_name or client.slack_user_id}"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Feeling:* {feeling_score}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Satisfaction:* {satisfaction_score}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Week:* {response.week_ending.strftime('%b %d, %Y')}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Submitted:* <!date^{int(response.submitted_at.timestamp())}^{{date_short}} {{time}}|{response.submitted_at}>"
                }
            ]
        },
        {
            "type": "divider"
        }
    ]

    # Additional thoughts
    if response.feeling_text:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Notes:*\n{response.feeling_text}"
            }
        })

    # Improvements
    if response.improvements:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Improvements:*\n{response.improvements}"
            }
        })

    # Blockers
    if response.blockers:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Blockers:*\n{response.blockers}"
            }
        })

    # Context footer
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Response time: {response.response_time_seconds // 60 if response.response_time_seconds else 0}m | ID: {client.id}"
            }
        ]
    })

    return blocks
