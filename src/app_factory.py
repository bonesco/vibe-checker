"""Slack Bolt app factory"""

import os
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, jsonify
from src.config import config
from src.utils.logger import setup_logger
from src.middleware.error_middleware import setup_error_handlers

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

    # Register global error handlers
    setup_error_handlers(app)

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
        return handler.handle(request)

    @flask_app.route("/health", methods=["GET"])
    def health_check():
        """
        Comprehensive health check endpoint.

        Returns status of:
        - App: Always ok if responding
        - Database: Connected if can query
        - Scheduler: Running if APScheduler is active
        """
        health = {
            "status": "ok",
            "app": "running",
            "database": "unknown",
            "scheduler": "unknown"
        }

        # Check database connection
        try:
            from sqlalchemy import text
            from src.database.session import get_session
            session = get_session()
            session.execute(text("SELECT 1"))
            session.close()
            health["database"] = "connected"
        except Exception as e:
            health["database"] = f"error: {str(e)[:50]}"
            health["status"] = "degraded"

        # Check scheduler
        try:
            from src.services.scheduler_service import get_scheduler
            scheduler = get_scheduler()
            if scheduler and scheduler.running:
                health["scheduler"] = "running"
                health["scheduled_jobs"] = len(scheduler.get_jobs())
            else:
                health["scheduler"] = "stopped"
        except Exception as e:
            health["scheduler"] = f"error: {str(e)[:50]}"

        # Always return 200 if app is responding - Railway needs this for deployment
        # The status field in the response body indicates actual health for monitoring
        return jsonify(health), 200

    @flask_app.route("/", methods=["GET"])
    def home():
        """Home page with app info"""
        return """
        <!DOCTYPE html>
        <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Vibe Check - Slack App</title>
                <style>
                    * { box-sizing: border-box; }
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 40px 20px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                    }
                    .card {
                        background: white;
                        border-radius: 16px;
                        padding: 40px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                        text-align: center;
                    }
                    h1 { color: #333; margin-bottom: 10px; }
                    .subtitle { color: #666; margin-bottom: 30px; }
                    .commands {
                        text-align: left;
                        background: #f8f9fa;
                        border-radius: 8px;
                        padding: 20px;
                        margin: 20px 0;
                    }
                    .commands h3 { margin-top: 0; color: #333; }
                    .commands code {
                        background: #e9ecef;
                        padding: 2px 6px;
                        border-radius: 4px;
                        font-size: 14px;
                    }
                    .commands ul { padding-left: 20px; }
                    .commands li { margin: 8px 0; color: #555; }
                    .status {
                        display: inline-block;
                        background: #28a745;
                        color: white;
                        padding: 4px 12px;
                        border-radius: 20px;
                        font-size: 12px;
                        margin-bottom: 20px;
                    }
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="status">Running</div>
                    <h1>Vibe Check</h1>
                    <p class="subtitle">Client feedback and standup management for Slack</p>

                    <div class="commands">
                        <h3>Quick Start</h3>
                        <ul>
                            <li><code>/vibe-help</code> - Show all commands</li>
                            <li><code>/vibe-add-client</code> - Add a client for standups</li>
                            <li><code>/vibe-test</code> - Send a test standup</li>
                        </ul>
                    </div>

                    <p style="color: #888; font-size: 14px;">
                        Health check: <a href="/health">/health</a>
                    </p>
                </div>
            </body>
        </html>
        """

    logger.info("Flask app configured")
    return flask_app
