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
                "text": "🎭 Weekly Vibe Check"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Hey! Let's check in on how this week went (ending {week_str})"
            }
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
                    "text": "Select feeling"
                },
                "options": [
                    {"text": {"type": "plain_text", "text": "😄 Great"}, "value": "5"},
                    {"text": {"type": "plain_text", "text": "🙂 Good"}, "value": "4"},
                    {"text": {"type": "plain_text", "text": "😐 Okay"}, "value": "3"},
                    {"text": {"type": "plain_text", "text": "😕 Not great"}, "value": "2"},
                    {"text": {"type": "plain_text", "text": "😞 Struggling"}, "value": "1"}
                ]
            }
        },
        {
            "type": "input",
            "block_id": f"feeling_text_{client_id}_{week_key}",
            "optional": True,
            "element": {
                "type": "plain_text_input",
                "action_id": "feeling_text_input",
                "multiline": True,
                "placeholder": {
                    "type": "plain_text",
                    "text": "Want to share more about how you're feeling?"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "💭 Additional thoughts (optional)"
            }
        },
        {
            "type": "input",
            "block_id": f"improvements_{client_id}_{week_key}",
            "optional": True,
            "element": {
                "type": "plain_text_input",
                "action_id": "improvements_input",
                "multiline": True,
                "placeholder": {
                    "type": "plain_text",
                    "text": "What could we improve?"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "💡 Suggestions for improvement"
            }
        },
        {
            "type": "input",
            "block_id": f"blockers_{client_id}_{week_key}",
            "optional": True,
            "element": {
                "type": "plain_text_input",
                "action_id": "blockers_input",
                "multiline": True,
                "placeholder": {
                    "type": "plain_text",
                    "text": "Any blockers or concerns?"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "🚧 Blockers (optional)"
            }
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
                    "text": "Rate satisfaction"
                },
                "options": [
                    {"text": {"type": "plain_text", "text": "⭐⭐⭐⭐⭐ Excellent"}, "value": "5"},
                    {"text": {"type": "plain_text", "text": "⭐⭐⭐⭐ Very Good"}, "value": "4"},
                    {"text": {"type": "plain_text", "text": "⭐⭐⭐ Good"}, "value": "3"},
                    {"text": {"type": "plain_text", "text": "⭐⭐ Fair"}, "value": "2"},
                    {"text": {"type": "plain_text", "text": "⭐ Needs Improvement"}, "value": "1"}
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
                        "text": "Submit Feedback"
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
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "✅ Feedback Submitted!"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Thank you for your feedback! We appreciate you taking the time to share your thoughts."
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
    # Emoji mapping for ratings
    feeling_emojis = ["😞", "😕", "😐", "🙂", "😄"]
    feeling_emoji = feeling_emojis[response.feeling_rating - 1] if response.feeling_rating else "❓"
    satisfaction_stars = "⭐" * (response.satisfaction_rating or 0)

    # Determine alert level
    alert_emoji = ""
    if response.needs_attention:
        alert_emoji = "🚨 "
    elif response.is_positive:
        alert_emoji = "✅ "

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{alert_emoji}{feeling_emoji} Weekly Feedback from {client.display_name or client.slack_user_id}"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Feeling:* {feeling_emoji} ({response.feeling_rating or 'N/A'}/5)"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Satisfaction:* {satisfaction_stars} ({response.satisfaction_rating or 'N/A'}/5)"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Week Ending:* {response.week_ending.strftime('%B %d, %Y')}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Submitted:* <!date^{int(response.submitted_at.timestamp())}^{{date_short_pretty}} at {{time}}|{response.submitted_at}>"
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
                "text": f"*Additional Thoughts:*\n{response.feeling_text}"
            }
        })

    # Improvements
    if response.improvements:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Suggestions for Improvement:*\n{response.improvements}"
            }
        })

    # Blockers
    if response.blockers:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Blockers/Concerns:*\n{response.blockers}"
            }
        })

    # Context footer
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Response time: {response.response_time_seconds // 60 if response.response_time_seconds else 0} minutes | Client ID: {client.id}"
            }
        ]
    })

    return blocks
