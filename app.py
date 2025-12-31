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


def main():
    """Initialize and start the Vibe Check Slack app"""

    logger.info("=" * 50)
    logger.info("Starting Vibe Check Slack App...")
    logger.info("=" * 50)

    # Validate environment configuration
    if not validate_environment():
        logger.error("Environment validation failed. Please check your configuration.")
        sys.exit(1)

    logger.info(f"Environment: {config.LOG_LEVEL}")
    logger.info(f"Port: {config.PORT}")
    logger.info(f"Database: {config.DATABASE_URL.split('@')[-1] if '@' in config.DATABASE_URL else 'configured'}")

    try:
        # Initialize database (creates tables if they don't exist)
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
        flask_app = create_flask_app(slack_app)

        # Start server
        logger.info("=" * 50)
        logger.info(f"🚀 Vibe Check is running on port {config.PORT}")
        logger.info(f"📝 OAuth Install URL: http://localhost:{config.PORT}/slack/install")
        logger.info(f"❤️  Health Check: http://localhost:{config.PORT}/health")
        logger.info("=" * 50)

        flask_app.run(
            host="0.0.0.0",
            port=config.PORT,
            debug=False
        )

    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


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


if __name__ == "__main__":
    main()
