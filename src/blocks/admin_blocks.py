"""Block Kit templates for admin commands"""

from typing import List, Dict, Any, Optional
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
                    "options": [
                        {
                            "value": "daily",
                            "text": {
                                "type": "plain_text",
                                "text": "Daily - Send standup request every day"
                            }
                        },
                        {
                            "value": "monday_only",
                            "text": {
                                "type": "plain_text",
                                "text": "Weekly - Send standup request on Mondays only"
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
            schedule_type = "Daily" if client.standup_config.schedule_type == "daily" else "Weekly (Mon)"
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
                    "`/vibe-set-channel` - Set the vibe check feedback channel\n"
                    "`/vibe-test` - Send a test standup to yourself\n"
                    "`/vibe-test-feedback` - Send a test feedback form to yourself\n"
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
                       "• Friday Vibe Check (weekly retrospective) is sent every Friday\n"
                       "• All responses are posted to your private vibe check channel\n"
                       "• Clients can submit responses using the interactive buttons"
            }
        }
    ]


def get_client_select_modal(
    action: str,
    clients: List[Client],
    title: str,
    submit_text: str,
    description: str
) -> Optional[Dict[str, Any]]:
    """
    Create a modal for selecting a client

    Args:
        action: Action type ('pause', 'resume', 'remove')
        clients: List of Client objects to show in dropdown
        title: Modal title
        submit_text: Submit button text
        description: Description text to show

    Returns:
        Modal view definition or None if no clients
    """
    if not clients:
        return None

    # Build options from clients
    options = []
    for client in clients:
        display = client.display_name or client.slack_user_id
        options.append({
            "text": {"type": "plain_text", "text": display[:75]},  # Slack limit
            "value": str(client.id)
        })

    return {
        "type": "modal",
        "callback_id": f"{action}_client_modal",
        "title": {
            "type": "plain_text",
            "text": title[:24]  # Slack limit
        },
        "submit": {
            "type": "plain_text",
            "text": submit_text
        },
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": description
                }
            },
            {
                "type": "input",
                "block_id": "client_select",
                "element": {
                    "type": "static_select",
                    "action_id": "client_select_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select a client"
                    },
                    "options": options
                },
                "label": {
                    "type": "plain_text",
                    "text": "Client"
                }
            }
        ]
    }


def get_pause_client_modal(clients: List[Client]) -> Optional[Dict[str, Any]]:
    """Create modal for pausing client standups"""
    # Filter to only show active (not paused) clients
    active_clients = [c for c in clients if c.standup_config and not c.standup_config.is_paused]
    return get_client_select_modal(
        action="pause",
        clients=active_clients,
        title="Pause Standups",
        submit_text="Pause",
        description="Select a client to pause their standup messages. They won't receive standups until resumed."
    )


def get_resume_client_modal(clients: List[Client]) -> Optional[Dict[str, Any]]:
    """Create modal for resuming client standups"""
    # Filter to only show paused clients
    paused_clients = [c for c in clients if c.standup_config and c.standup_config.is_paused]
    return get_client_select_modal(
        action="resume",
        clients=paused_clients,
        title="Resume Standups",
        submit_text="Resume",
        description="Select a client to resume their standup messages."
    )


def get_remove_client_modal(clients: List[Client]) -> Optional[Dict[str, Any]]:
    """Create modal for removing a client"""
    return get_client_select_modal(
        action="remove",
        clients=clients,
        title="Remove Client",
        submit_text="Remove",
        description="⚠️ *Warning:* This will permanently remove the client and all their response history."
    )


def get_set_channel_modal() -> Dict[str, Any]:
    """Create modal for setting the vibe check channel"""
    return {
        "type": "modal",
        "callback_id": "set_channel_modal",
        "title": {
            "type": "plain_text",
            "text": "Set Vibe Channel"
        },
        "submit": {
            "type": "plain_text",
            "text": "Set Channel"
        },
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Select the channel where client feedback summaries will be posted."
                }
            },
            {
                "type": "input",
                "block_id": "channel_select",
                "element": {
                    "type": "channels_select",
                    "action_id": "channel_select_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select a channel"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "Vibe Check Channel"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "💡 *Tip:* Use a private channel for confidential feedback."
                    }
                ]
            }
        ]
    }


def get_no_clients_message(action: str) -> List[Dict[str, Any]]:
    """Get message blocks when no clients are available for an action"""
    messages = {
        "pause": "No active clients to pause. All clients are either already paused or don't have standup configs.",
        "resume": "No paused clients to resume. Use `/vibe-pause` to pause a client first.",
        "remove": "No clients found. Use `/vibe-add-client` to add one."
    }
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": messages.get(action, "No clients found.")
            }
        }
    ]
