"""Slack API retry utility with exponential backoff"""

import time
import random
from functools import wraps
from typing import Callable, TypeVar, Any
from slack_sdk.errors import SlackApiError
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

T = TypeVar('T')


def slack_api_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True
) -> Callable:
    """
    Decorator for retrying Slack API calls with exponential backoff.

    Handles:
    - Rate limiting (429 errors) with Retry-After header
    - Transient server errors (500, 502, 503, 504)
    - Network timeouts

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to prevent thundering herd

    Example:
        @slack_api_retry(max_retries=3)
        def send_message(client, channel, text):
            return client.chat_postMessage(channel=channel, text=text)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except SlackApiError as e:
                    last_exception = e
                    error = e.response.get('error', 'unknown_error')

                    # Check if this is a retryable error
                    if error == 'ratelimited':
                        # Use Retry-After header if available
                        retry_after = int(e.response.headers.get('Retry-After', base_delay))
                        delay = min(retry_after, max_delay)
                        logger.warning(
                            f"Rate limited on {func.__name__}, waiting {delay}s "
                            f"(attempt {attempt + 1}/{max_retries + 1})"
                        )
                    elif error in ('internal_error', 'service_unavailable', 'timeout'):
                        # Server-side errors - use exponential backoff
                        delay = min(base_delay * (exponential_base ** attempt), max_delay)
                        if jitter:
                            delay = delay * (0.5 + random.random())
                        logger.warning(
                            f"Slack API error '{error}' on {func.__name__}, "
                            f"retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries + 1})"
                        )
                    else:
                        # Non-retryable error (invalid_auth, channel_not_found, etc.)
                        logger.error(f"Slack API error '{error}' on {func.__name__}: {e}")
                        raise

                    if attempt < max_retries:
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Max retries ({max_retries}) exceeded for {func.__name__}"
                        )
                        raise

                except Exception as e:
                    # Network errors, timeouts, etc.
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (exponential_base ** attempt), max_delay)
                        if jitter:
                            delay = delay * (0.5 + random.random())
                        logger.warning(
                            f"Error on {func.__name__}: {e}, "
                            f"retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries + 1})"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}"
                        )
                        raise

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def send_message_with_retry(
    client,
    channel: str,
    text: str,
    blocks: list = None,
    **kwargs
) -> dict:
    """
    Send a Slack message with automatic retry on failure.

    Args:
        client: Slack WebClient instance
        channel: Channel or user ID to send to
        text: Fallback text for the message
        blocks: Optional Block Kit blocks
        **kwargs: Additional arguments for chat_postMessage

    Returns:
        Slack API response dict
    """
    @slack_api_retry(max_retries=3)
    def _send():
        return client.chat_postMessage(
            channel=channel,
            text=text,
            blocks=blocks,
            **kwargs
        )

    return _send()


def update_message_with_retry(
    client,
    channel: str,
    ts: str,
    text: str,
    blocks: list = None,
    **kwargs
) -> dict:
    """
    Update a Slack message with automatic retry on failure.

    Args:
        client: Slack WebClient instance
        channel: Channel ID
        ts: Message timestamp
        text: Fallback text for the message
        blocks: Optional Block Kit blocks
        **kwargs: Additional arguments for chat_update

    Returns:
        Slack API response dict
    """
    @slack_api_retry(max_retries=3)
    def _update():
        return client.chat_update(
            channel=channel,
            ts=ts,
            text=text,
            blocks=blocks,
            **kwargs
        )

    return _update()
