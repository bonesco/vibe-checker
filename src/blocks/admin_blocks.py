"""Block Kit templates for admin commands"""

from typing import List, Dict, Any
from src.models.client import Client


def get_add_client_modal() -> Dict[str, Any]:
    """
    Create modal for adding a new client

    Returns:
        Modal view definition
    """
    return {
        "type": "modal",
        "callback_id": "add_client_modal",
        "title": {
            "type": "plain_text",
            "text": "Add New Client"
        },
        "submit": {
            "type": "plain_text",
            "text": "Add Client"
        },
        "blocks": [
            {
                "type": "input",
                "block_id": "user_select",
                "element": {
                    "type": "users_select",
                    "action_id": "user_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select a user"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "Client User"
                }
            },
            {
                "type": "input",
                "block_id": "timezone",
                "element": {
                    "type": "static_select",
                    "action_id": "timezone_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select timezone"
                    },
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "America/New_York (EST/EDT)"},
                        "value": "America/New_York"
                    },
                    "options": [
                        {"text": {"type": "plain_text", "text": "America/New_York (EST/EDT)"}, "value": "America/New_York"},
                        {"text": {"type": "plain_text", "text": "America/Chicago (CST/CDT)"}, "value": "America/Chicago"},
                        {"text": {"type": "plain_text", "text": "America/Denver (MST/MDT)"}, "value": "America/Denver"},
                        {"text": {"type": "plain_text", "text": "America/Los_Angeles (PST/PDT)"}, "value": "America/Los_Angeles"},
                        {"text": {"type": "plain_text", "text": "Europe/London (GMT/BST)"}, "value": "Europe/London"},
                        {"text": {"type": "plain_text", "text": "Europe/Paris (CET/CEST)"}, "value": "Europe/Paris"},
                        {"text": {"type": "plain_text", "text": "Asia/Tokyo (JST)"}, "value": "Asia/Tokyo"},
                        {"text": {"type": "plain_text", "text": "UTC"}, "value": "UTC"}
                    ]
                },
                "label": {
                    "type": "plain_text",
                    "text": "Timezone"
                }
            },
            {
                "type": "input",
                "block_id": "schedule_type",
                "element": {
                    "type": "radio_buttons",
                    "action_id": "schedule_type_select",
                    "initial_option": {
                        "value": "daily",
                        "text": {"type": "plain_text", "text": "Daily"}
                    },
                    "options": [
                        {
                            "value": "daily",
                            "text": {
                                "type": "plain_text",
                                "text": "Daily"
                            },
                            "description": {
                                "type": "plain_text",
                                "text": "Send standup request every day"
                            }
                        },
                        {
                            "value": "monday_only",
                            "text": {
                                "type": "plain_text",
                                "text": "Monday Only"
                            },
                            "description": {
                                "type": "plain_text",
                                "text": "Send standup request only on Mondays"
                            }
                        }
                    ]
                },
                "label": {
                    "type": "plain_text",
                    "text": "Standup Schedule"
                }
            },
            {
                "type": "input",
                "block_id": "standup_time",
                "element": {
                    "type": "timepicker",
                    "action_id": "time_select",
                    "initial_time": "09:00",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select time"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "Standup Time"
                }
            }
        ]
    }


def get_client_list_blocks(clients: List[Client]) -> List[Dict[str, Any]]:
    """
    Create blocks showing list of clients

    Args:
        clients: List of Client objects

    Returns:
        List of Block Kit blocks
    """
    if not clients:
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "No clients found. Use `/vibe-add-client` to add one."
                }
            }
        ]

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📋 Active Clients ({len(clients)})"
            }
        }
    ]

    for client in clients:
        status_emoji = "✅" if client.is_active else "⏸️"
        standup_info = "No standup configured"

        if client.standup_config:
            schedule_type = "Daily" if client.standup_config.schedule_type == "daily" else "Mondays"
            paused = " (Paused)" if client.standup_config.is_paused else ""
            standup_info = f"{schedule_type} at {client.standup_config.schedule_time.strftime('%I:%M %p')}{paused}"

        feedback_info = "✅ Enabled" if (client.feedback_config and client.feedback_config.is_enabled) else "❌ Disabled"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"{status_emoji} *<@{client.slack_user_id}>*\n"
                    f"• Standup: {standup_info}\n"
                    f"• Feedback: {feedback_info}\n"
                    f"• Timezone: {client.timezone}"
                )
            }
        })
        blocks.append({"type": "divider"})

    return blocks


def get_help_blocks() -> List[Dict[str, Any]]:
    """
    Create help documentation blocks

    Returns:
        List of Block Kit blocks
    """
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🎭 Vibe Check - Help"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Available Commands:*"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "`/vibe-add-client` - Add a new client to receive standups\n"
                    "`/vibe-remove-client` - Remove a client\n"
                    "`/vibe-list-clients` - List all active clients\n"
                    "`/vibe-pause` - Pause standups for a client\n"
                    "`/vibe-resume` - Resume standups for a client\n"
                    "`/vibe-test` - Send a test standup to yourself\n"
                    "`/vibe-help` - Show this help message"
                )
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*How it works:*\n"
                       "• Daily standups are sent via DM at the configured time\n"
                       "• Weekly feedback is sent every Friday\n"
                       "• All feedback is posted to your private vibe check channel\n"
                       "• Clients can submit responses using the interactive buttons"
            }
        }
    ]
