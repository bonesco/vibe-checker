"""Slack Bolt app factory"""

import os
import secrets
from datetime import timedelta
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

    # Configure Flask for sessions (used by admin dashboard)
    flask_app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))
    flask_app.permanent_session_lifetime = timedelta(hours=24)

    # Register admin dashboard blueprint
    from src.routes.admin_routes import admin_bp
    flask_app.register_blueprint(admin_bp)

    # Register OAuth routes for multi-workspace installation
    from src.routes.oauth_routes import oauth_bp
    flask_app.register_blueprint(oauth_bp)

    # Setup security middleware (rate limiting, security headers)
    from src.middleware.security_middleware import setup_security_middleware
    setup_security_middleware(flask_app)

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
                health["status"] = "degraded"
        except Exception as e:
            health["scheduler"] = f"error: {str(e)[:50]}"

        status_code = 200 if health["status"] == "ok" else 503
        return jsonify(health), status_code

    @flask_app.route("/", methods=["GET"])
    def home():
        """Home page with app info"""
        return """
        <!DOCTYPE html>
        <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Vibe Check - Slack App for Team Check-ins</title>
                <meta name="description" content="Automated daily standups and Friday vibe checks for Slack. Keep your team connected with fun, authentic check-ins.">
                <style>
                    * { box-sizing: border-box; margin: 0; padding: 0; }
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        padding: 40px 20px;
                    }
                    .container {
                        max-width: 700px;
                        margin: 0 auto;
                    }
                    .hero {
                        background: white;
                        border-radius: 20px;
                        padding: 50px 40px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                        text-align: center;
                        margin-bottom: 24px;
                    }
                    .logo { font-size: 48px; margin-bottom: 8px; }
                    h1 { color: #333; font-size: 36px; margin-bottom: 12px; }
                    .tagline { color: #666; font-size: 18px; margin-bottom: 32px; }
                    .slack-btn {
                        display: inline-flex;
                        align-items: center;
                        padding: 16px 32px;
                        background: #4A154B;
                        color: white;
                        text-decoration: none;
                        border-radius: 8px;
                        font-size: 18px;
                        font-weight: 600;
                        transition: all 0.2s;
                        margin-bottom: 24px;
                    }
                    .slack-btn:hover {
                        background: #611f69;
                        transform: translateY(-2px);
                        box-shadow: 0 4px 12px rgba(74, 21, 75, 0.4);
                    }
                    .slack-btn svg {
                        width: 24px;
                        height: 24px;
                        margin-right: 12px;
                    }
                    .features {
                        display: grid;
                        grid-template-columns: repeat(2, 1fr);
                        gap: 16px;
                        margin: 32px 0;
                        text-align: left;
                    }
                    .feature {
                        background: #f8f9fa;
                        padding: 20px;
                        border-radius: 12px;
                    }
                    .feature h3 {
                        color: #333;
                        font-size: 16px;
                        margin-bottom: 6px;
                    }
                    .feature p {
                        color: #666;
                        font-size: 14px;
                        line-height: 1.4;
                    }
                    .links {
                        margin-top: 24px;
                        padding-top: 24px;
                        border-top: 1px solid #eee;
                    }
                    .links a {
                        color: #667eea;
                        text-decoration: none;
                        margin: 0 12px;
                        font-size: 14px;
                    }
                    .links a:hover { text-decoration: underline; }
                    .footer {
                        text-align: center;
                        color: rgba(255,255,255,0.8);
                        font-size: 14px;
                    }
                    .footer a { color: white; }
                    @media (max-width: 500px) {
                        .features { grid-template-columns: 1fr; }
                        .hero { padding: 30px 20px; }
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="hero">
                        <div class="logo">✨</div>
                        <h1>Vibe Check</h1>
                        <p class="tagline">Daily standups & Friday vibe checks for Slack</p>

                        <a href="/slack/add" class="slack-btn">
                            <svg viewBox="0 0 24 24" fill="currentColor">
                                <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"/>
                            </svg>
                            Add to Slack
                        </a>

                        <div class="features">
                            <div class="feature">
                                <h3>Daily Standups</h3>
                                <p>Automated DMs to check in on progress, plans, and blockers</p>
                            </div>
                            <div class="feature">
                                <h3>Friday Vibe Checks</h3>
                                <p>Fun end-of-week check-ins to see how everyone's really doing</p>
                            </div>
                            <div class="feature">
                                <h3>Flexible Scheduling</h3>
                                <p>Daily or weekly, with timezone support for remote teams</p>
                            </div>
                            <div class="feature">
                                <h3>Private & Secure</h3>
                                <p>Responses stay private until shared to your team channel</p>
                            </div>
                        </div>

                        <div class="links">
                            <a href="/health">Health Status</a>
                            <a href="/admin">Admin Dashboard</a>
                        </div>
                    </div>

                    <p class="footer">
                        Made with care for happier teams
                    </p>
                </div>
            </body>
        </html>
        """

    logger.info("Flask app configured")
    return flask_app
