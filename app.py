#!/usr/bin/env python3
"""
Vibe Check Slack App - Main Entry Point

Professional client communication app with daily standups and weekly feedback collection
"""

import os
import sys
from src.config import config, validate_environment
from src.utils.logger import setup_logger
from src.app_factory import create_slack_app, create_flask_app
from src.database.session import init_db

logger = setup_logger(__name__)


def register_handlers(app):
    """
    Register all Slack event handlers, commands, and actions

    Args:
        app: Slack Bolt App instance
    """
    from src.handlers import commands, actions, views, events

    # Register command handlers
    logger.info("Registering slash commands...")
    commands.register(app)

    # Register action handlers (Block Kit interactions)
    logger.info("Registering action handlers...")
    actions.register(app)

    # Register view handlers (Modal submissions)
    logger.info("Registering view handlers...")
    views.register(app)

    # Register event handlers
    logger.info("Registering event handlers...")
    events.register(app)

    # Global error handler
    @app.error
    def custom_error_handler(error, body, logger):
        """Handle errors globally"""
        logger.exception(f"Error: {error}")
        logger.error(f"Request body: {body}")
        return {
            "response_type": "ephemeral",
            "text": f"Sorry, something went wrong: {str(error)}\nOur team has been notified."
        }

    logger.info("All handlers registered successfully")


def create_app():
    """
    Create and configure the Flask app for gunicorn

    Returns:
        Configured Flask app
    """
    logger.info("=" * 50)
    logger.info("Starting Vibe Check Slack App...")
    logger.info("=" * 50)

    # Validate environment configuration
    if not validate_environment():
        logger.error("Environment validation failed. Please check your configuration.")
        sys.exit(1)

    # Initialize database
    logger.info("Initializing database...")
    init_db()

    # Create Slack Bolt app
    logger.info("Creating Slack app...")
    slack_app = create_slack_app()

    # Register handlers
    logger.info("Registering event handlers...")
    register_handlers(slack_app)

    # Initialize scheduler
    logger.info("Initializing job scheduler...")
    from src.services.scheduler_service import init_scheduler
    init_scheduler()

    # Create Flask app
    logger.info("Creating Flask app...")
    flask_application = create_flask_app(slack_app)

    logger.info("=" * 50)
    logger.info(f"Vibe Check is ready on port {config.PORT}")
    logger.info("=" * 50)

    return flask_application


# Create flask_app at module level for gunicorn
flask_app = create_app()


if __name__ == "__main__":
    flask_app.run(
        host="0.0.0.0",
        port=config.PORT,
        debug=False
    )
