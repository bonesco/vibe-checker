"""Global error handling middleware"""

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def setup_error_handlers(app):
    """Set up global error handlers for Slack Bolt app"""

    @app.error
    def custom_error_handler(error, body):
        """
        Handle all unhandled errors from Slack Bolt handlers.

        Args:
            error: The exception that was raised
            body: The request body from Slack
        """
        logger.exception(f"Unhandled error: {error}")
        logger.error(f"Request body: {body}")

        # Note: Return value from error handler is not used by Slack Bolt
        # The error is logged and Slack receives an error response

    logger.info("Error handlers configured")
