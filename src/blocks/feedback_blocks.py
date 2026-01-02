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
                "text": "🎭 Friday Vibe Check - Weekly Retrospective"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Hey! It's time for your weekly retrospective for the week ending *{week_str}*.\nLet's reflect on what worked, what didn't, and how we can improve."
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
                "text": "*How are you feeling about this week overall?*"
            },
            "accessory": {
                "type": "static_select",
                "action_id": "feeling_rating_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select feeling"
                },
                "options": [
                    {"text": {"type": "plain_text", "text": "😄 Great - Productive and energized"}, "value": "5"},
                    {"text": {"type": "plain_text", "text": "🙂 Good - Solid progress made"}, "value": "4"},
                    {"text": {"type": "plain_text", "text": "😐 Okay - Some ups and downs"}, "value": "3"},
                    {"text": {"type": "plain_text", "text": "😕 Not great - Challenging week"}, "value": "2"},
                    {"text": {"type": "plain_text", "text": "😞 Struggling - Need support"}, "value": "1"}
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
                    "text": "What were your biggest wins or accomplishments this week? What are you proud of?"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "🏆 What went well this week?"
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
                    "text": "What challenges did you face? What slowed you down or didn't go as planned?"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "🚧 What didn't go well?"
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
                    "text": "What would help you be more successful? Process changes, tools, communication, support needed?"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "💡 What can we improve for next week?"
            }
        },
        {
            "type": "section",
            "block_id": f"satisfaction_rating_{client_id}_{week_key}",
            "text": {
                "type": "mrkdwn",
                "text": "*How satisfied are you with the progress and collaboration this week?*"
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
                        "text": "Submit Vibe Check"
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
                "text": f"{alert_emoji}{feeling_emoji} Weekly Retrospective from {client.display_name or client.slack_user_id}"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Overall Feeling:* {feeling_emoji} ({response.feeling_rating or 'N/A'}/5)"
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

    # What went well
    if response.feeling_text:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🏆 What went well:*\n{response.feeling_text}"
            }
        })

    # What didn't go well
    if response.blockers:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🚧 What didn't go well:*\n{response.blockers}"
            }
        })

    # Improvements for next week
    if response.improvements:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*💡 Improvements for next week:*\n{response.improvements}"
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
