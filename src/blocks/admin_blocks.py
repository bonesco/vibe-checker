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
            "text": "ADD CLIENT"
        },
        "submit": {
            "type": "plain_text",
            "text": "Add"
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
                        "text": "Select user"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "USER"
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
                        "text": "Select"
                    },
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "New York (EST/EDT)"},
                        "value": "America/New_York"
                    },
                    "options": [
                        {"text": {"type": "plain_text", "text": "New York (EST/EDT)"}, "value": "America/New_York"},
                        {"text": {"type": "plain_text", "text": "Chicago (CST/CDT)"}, "value": "America/Chicago"},
                        {"text": {"type": "plain_text", "text": "Denver (MST/MDT)"}, "value": "America/Denver"},
                        {"text": {"type": "plain_text", "text": "Los Angeles (PST/PDT)"}, "value": "America/Los_Angeles"},
                        {"text": {"type": "plain_text", "text": "London (GMT/BST)"}, "value": "Europe/London"},
                        {"text": {"type": "plain_text", "text": "Paris (CET/CEST)"}, "value": "Europe/Paris"},
                        {"text": {"type": "plain_text", "text": "Tokyo (JST)"}, "value": "Asia/Tokyo"},
                        {"text": {"type": "plain_text", "text": "UTC"}, "value": "UTC"}
                    ]
                },
                "label": {
                    "type": "plain_text",
                    "text": "TIMEZONE"
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
                                "text": "Every day"
                            }
                        },
                        {
                            "value": "monday_only",
                            "text": {
                                "type": "plain_text",
                                "text": "Weekly"
                            },
                            "description": {
                                "type": "plain_text",
                                "text": "Mondays only"
                            }
                        }
                    ]
                },
                "label": {
                    "type": "plain_text",
                    "text": "SCHEDULE"
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
                        "text": "Select"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "TIME"
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
                    "text": "No clients. Run `/vibe-add-client` to add one."
                }
            }
        ]

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"CLIENTS [{len(clients)}]"
            }
        }
    ]

    for client in clients:
        status = "ACTIVE" if client.is_active else "PAUSED"
        standup_info = "Not configured"

        if client.standup_config:
            schedule_type = "Daily" if client.standup_config.schedule_type == "daily" else "Weekly"
            paused = " [PAUSED]" if client.standup_config.is_paused else ""
            standup_info = f"{schedule_type} @ {client.standup_config.schedule_time.strftime('%H:%M')}{paused}"

        feedback_status = "ON" if (client.feedback_config and client.feedback_config.is_enabled) else "OFF"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*<@{client.slack_user_id}>* [{status}]\n"
                    f"Standup: {standup_info}\n"
                    f"Feedback: {feedback_status}\n"
                    f"TZ: {client.timezone}"
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
                "text": "VIBE CHECK"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Commands*"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "`/vibe-add-client` — Add client\n"
                    "`/vibe-remove-client` — Remove client\n"
                    "`/vibe-list-clients` — List clients\n"
                    "`/vibe-pause` — Pause standups\n"
                    "`/vibe-resume` — Resume standups\n"
                    "`/vibe-set-channel` — Set feedback channel\n"
                    "`/vibe-test` — Send test standup\n"
                    "`/vibe-help` — This message"
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
                "text": "*How it works*\n"
                       "Daily standups via DM at scheduled time.\n"
                       "Weekly feedback every Friday.\n"
                       "All responses posted to your channel."
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
                        "text": "Select"
                    },
                    "options": options
                },
                "label": {
                    "type": "plain_text",
                    "text": "CLIENT"
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
        title="PAUSE",
        submit_text="Pause",
        description="Select client to pause. They won't receive standups until resumed."
    )


def get_resume_client_modal(clients: List[Client]) -> Optional[Dict[str, Any]]:
    """Create modal for resuming client standups"""
    # Filter to only show paused clients
    paused_clients = [c for c in clients if c.standup_config and c.standup_config.is_paused]
    return get_client_select_modal(
        action="resume",
        clients=paused_clients,
        title="RESUME",
        submit_text="Resume",
        description="Select client to resume standups."
    )


def get_remove_client_modal(clients: List[Client]) -> Optional[Dict[str, Any]]:
    """Create modal for removing a client"""
    return get_client_select_modal(
        action="remove",
        clients=clients,
        title="REMOVE",
        submit_text="Remove",
        description="*Warning:* This permanently removes the client and all history."
    )


def get_set_channel_modal() -> Dict[str, Any]:
    """Create modal for setting the vibe check channel"""
    return {
        "type": "modal",
        "callback_id": "set_channel_modal",
        "title": {
            "type": "plain_text",
            "text": "SET CHANNEL"
        },
        "submit": {
            "type": "plain_text",
            "text": "Set"
        },
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Select channel for feedback summaries."
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
                        "text": "Select"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "CHANNEL"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Use a private channel for confidential feedback."
                    }
                ]
            }
        ]
    }


def get_no_clients_message(action: str) -> List[Dict[str, Any]]:
    """Get message blocks when no clients are available for an action"""
    messages = {
        "pause": "No active clients to pause.",
        "resume": "No paused clients to resume.",
        "remove": "No clients found."
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
