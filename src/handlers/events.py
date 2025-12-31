"""Event handlers"""

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def register(app):
    """Register all event handlers"""

    @app.event("app_home_opened")
    def handle_app_home_opened(event, client):
        """Handle App Home tab opened"""
        # Future feature: Show app home with stats and quick actions
        logger.info(f"App home opened by user {event['user']}")

    @app.event("team_join")
    def handle_team_join(event, client):
        """Handle new team member joining"""
        logger.info(f"New team member joined: {event['user']['id']}")

    logger.info("Event handlers registered")
