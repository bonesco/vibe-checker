"""Input validation utilities"""

import re
from typing import Optional
from datetime import time
import pytz


def validate_email(email: str) -> bool:
    """
    Validate email address format

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_timezone(timezone_str: str) -> bool:
    """
    Validate timezone string against pytz database

    Args:
        timezone_str: Timezone string (e.g., 'America/New_York')

    Returns:
        True if valid timezone, False otherwise
    """
    try:
        pytz.timezone(timezone_str)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False


def validate_time_string(time_str: str) -> Optional[time]:
    """
    Validate and parse time string in HH:MM format

    Args:
        time_str: Time string (e.g., '09:00', '14:30')

    Returns:
        time object if valid, None otherwise
    """
    try:
        parts = time_str.split(':')
        if len(parts) != 2:
            return None

        hour, minute = int(parts[0]), int(parts[1])

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None

        return time(hour=hour, minute=minute)
    except (ValueError, AttributeError):
        return None


def validate_slack_user_id(user_id: str) -> bool:
    """
    Validate Slack user ID format

    Args:
        user_id: Slack user ID (should start with 'U')

    Returns:
        True if valid format, False otherwise
    """
    return bool(user_id and user_id.startswith('U') and len(user_id) >= 9)


def validate_slack_channel_id(channel_id: str) -> bool:
    """
    Validate Slack channel ID format

    Args:
        channel_id: Slack channel ID (should start with 'C')

    Returns:
        True if valid format, False otherwise
    """
    return bool(channel_id and channel_id.startswith('C') and len(channel_id) >= 9)


def validate_slack_team_id(team_id: str) -> bool:
    """
    Validate Slack team/workspace ID format

    Args:
        team_id: Slack team ID (should start with 'T')

    Returns:
        True if valid format, False otherwise
    """
    return bool(team_id and team_id.startswith('T') and len(team_id) >= 9)


def validate_schedule_type(schedule_type: str) -> bool:
    """
    Validate standup schedule type

    Args:
        schedule_type: Schedule type ('daily' or 'monday_only')

    Returns:
        True if valid, False otherwise
    """
    return schedule_type in ['daily', 'monday_only']


def validate_rating(rating: int, min_val: int = 1, max_val: int = 5) -> bool:
    """
    Validate rating value is within range

    Args:
        rating: Rating value
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        True if valid, False otherwise
    """
    return isinstance(rating, int) and min_val <= rating <= max_val


# Text input limits for Block Kit and database storage
TEXT_LIMITS = {
    'accomplishments': 3000,
    'working_on': 3000,
    'blockers': 3000,
    'feeling_text': 3000,
    'improvements': 3000,
    'display_name': 255,
    'default': 3000
}


def sanitize_text_input(text: Optional[str], field_name: str = 'default') -> str:
    """
    Sanitize and truncate text input to safe limits.

    Args:
        text: Input text (may be None)
        field_name: Name of the field for limit lookup

    Returns:
        Sanitized text, empty string if None
    """
    if text is None:
        return ""

    # Get limit for this field
    limit = TEXT_LIMITS.get(field_name, TEXT_LIMITS['default'])

    # Strip whitespace and truncate
    sanitized = text.strip()[:limit]

    return sanitized


def validate_text_length(text: str, field_name: str = 'default') -> bool:
    """
    Check if text is within allowed length.

    Args:
        text: Text to validate
        field_name: Name of the field for limit lookup

    Returns:
        True if within limits, False otherwise
    """
    if text is None:
        return True

    limit = TEXT_LIMITS.get(field_name, TEXT_LIMITS['default'])
    return len(text) <= limit
