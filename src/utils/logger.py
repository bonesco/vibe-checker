"""Structured JSON logging configuration for Railway deployment"""

import logging
import sys
from pythonjsonlogger import jsonlogger
from src.config import config


def setup_logger(name: str = None) -> logging.Logger:
    """
    Configure structured JSON logger for the application

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(getattr(logging, config.LOG_LEVEL.upper()))

        # JSON formatter for structured logging
        log_handler = logging.StreamHandler(sys.stdout)
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d'
        )
        log_handler.setFormatter(formatter)
        logger.addHandler(log_handler)

    return logger


def log_with_context(logger: logging.Logger, level: int, message: str, **context):
    """
    Log a message with additional context data

    Args:
        logger: Logger instance
        level: Logging level (logging.INFO, logging.ERROR, etc.)
        message: Log message
        **context: Additional context key-value pairs

    Example:
        >>> logger = setup_logger(__name__)
        >>> log_with_context(
        ...     logger,
        ...     logging.INFO,
        ...     "Standup sent",
        ...     workspace_id=123,
        ...     client_id=456
        ... )
    """
    logger.log(level, message, extra=context)


# Create default application logger
app_logger = setup_logger('vibe_check')
