"""Slack Bolt app factory"""

import os
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, jsonify
from src.config import config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_slack_app() -> App:
    """
    Create and configure Slack Bolt app in single-workspace mode.

    Returns:
        Configured Slack Bolt App instance
    """
    bot_token = config.SLACK_BOT_TOKEN
    signing_secret = config.SLACK_SIGNING_SECRET

    if not bot_token:
        raise ValueError("SLACK_BOT_TOKEN is required")

    if not signing_secret:
        raise ValueError("SLACK_SIGNING_SECRET is required")

    logger.info("Creating Slack app in single-workspace mode")

    # IMPORTANT: Remove OAuth-related env vars so Slack Bolt doesn't auto-detect OAuth mode
    for env_var in ['SLACK_BOT_TOKEN', 'SLACK_CLIENT_ID', 'SLACK_CLIENT_SECRET']:
        if env_var in os.environ:
            del os.environ[env_var]

    # Create app with explicit token - no OAuth
    app = App(
        token=bot_token,
        signing_secret=signing_secret
    )

    logger.info("Slack app created successfully")
    return app


def create_flask_app(slack_app: App) -> Flask:
    """
    Create Flask app for handling HTTP requests

    Args:
        slack_app: Configured Slack Bolt App

    Returns:
        Flask application instance
    """
    flask_app = Flask(__name__)
    handler = SlackRequestHandler(slack_app)

    @flask_app.route("/slack/events", methods=["POST"])
    def slack_events():
        """Handle Slack events and interactivity"""
        # Log incoming requests for debugging
        logger.info(f"Received Slack request: {request.content_type}")
        try:
            result = handler.handle(request)
            logger.info(f"Slack request handled successfully")
            return result
        except Exception as e:
            logger.error(f"Error handling Slack request: {e}", exc_info=True)
            raise

    @flask_app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint for Railway"""
        return jsonify({"status": "ok"}), 200

    @flask_app.route("/", methods=["GET"])
    def home():
        """Home page"""
        return """
        <html>
            <head>
                <title>Vibe Check - Slack App</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        max-width: 600px;
                        margin: 100px auto;
                        padding: 20px;
                        text-align: center;
                    }
                    h1 { color: #333; }
                    p { color: #666; }
                </style>
            </head>
            <body>
                <h1>Vibe Check</h1>
                <p>Slack app is running. Use /vibe-help in Slack to get started.</p>
            </body>
        </html>
        """

    logger.info("Flask app configured")
    return flask_app
