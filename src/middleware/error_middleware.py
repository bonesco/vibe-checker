"""Global error handling middleware"""

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def setup_error_handlers(app):
    """Set up global error handlers"""

    @app.error
    def custom_error_handler(error, body, logger_obj):
        """Handle all unhandled errors"""
        logger.exception(f"Unhandled error: {error}")
        logger.error(f"Request body: {body}")

        # Return user-friendly error message
        return {
            "response_type": "ephemeral",
            "text": "❌ Sorry, something went wrong. Our team has been notified. Please try again later."
        }

    logger.info("Error handlers configured")
