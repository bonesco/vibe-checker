"""Block Kit templates for standup messages"""

from datetime import date
from typing import List, Dict, Any


def get_standup_message_blocks(client_id: int, scheduled_date: date) -> List[Dict[str, Any]]:
    """
    Create Block Kit blocks for standup DM

    Args:
        client_id: Client database ID
        scheduled_date: Date this standup is for

    Returns:
        List of Block Kit blocks
    """
    date_str = scheduled_date.strftime('%A, %B %d, %Y')
    date_key = scheduled_date.isoformat()

    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📋 Daily Standup Check-in"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Good morning! Time for your standup for *{date_str}*"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "input",
            "block_id": f"accomplishments_{client_id}_{date_key}",
            "element": {
                "type": "plain_text_input",
                "action_id": "accomplishments_input",
                "multiline": True,
                "placeholder": {
                    "type": "plain_text",
                    "text": "What did you accomplish yesterday/last week?"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "✅ Accomplishments"
            }
        },
        {
            "type": "input",
            "block_id": f"working_on_{client_id}_{date_key}",
            "element": {
                "type": "plain_text_input",
                "action_id": "working_on_input",
                "multiline": True,
                "placeholder": {
                    "type": "plain_text",
                    "text": "What are you working on today/this week?"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "🎯 Today's Focus"
            }
        },
        {
            "type": "input",
            "block_id": f"blockers_{client_id}_{date_key}",
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
            "type": "actions",
            "block_id": f"standup_actions_{client_id}_{date_key}",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Submit Standup"
                    },
                    "style": "primary",
                    "action_id": f"submit_standup",
                    "value": f"{client_id}|{date_key}"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Skip Today"
                    },
                    "action_id": f"skip_standup",
                    "value": f"{client_id}|{date_key}"
                }
            ]
        }
    ]


def get_standup_confirmation_blocks(submitted: bool = True) -> List[Dict[str, Any]]:
    """
    Create confirmation message after standup submission

    Args:
        submitted: True if submitted, False if skipped

    Returns:
        List of Block Kit blocks
    """
    if submitted:
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "✅ Standup Submitted!"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Thanks for your update! Your standup has been recorded."
                }
            }
        ]
    else:
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "👍 Standup Skipped"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "No problem! We've noted that you skipped today's standup."
                }
            }
        ]
