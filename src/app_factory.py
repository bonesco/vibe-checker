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
                <title>Vibe Check - Async standups for Slack</title>
                <meta name="description" content="Automated daily standups and Friday vibe checks for Slack teams.">
                <link rel="preconnect" href="https://fonts.googleapis.com">
                <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
                <style>
                    * { box-sizing: border-box; margin: 0; padding: 0; }
                    body {
                        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                        background: #0a0a0a;
                        color: #fafafa;
                        min-height: 100vh;
                        -webkit-font-smoothing: antialiased;
                    }
                    .nav {
                        padding: 20px 40px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        border-bottom: 1px solid rgba(255,255,255,0.1);
                    }
                    .nav-brand {
                        font-weight: 600;
                        font-size: 15px;
                        color: #fafafa;
                        text-decoration: none;
                        display: flex;
                        align-items: center;
                        gap: 8px;
                    }
                    .nav-links { display: flex; gap: 32px; }
                    .nav-links a {
                        color: #888;
                        text-decoration: none;
                        font-size: 14px;
                        transition: color 0.15s;
                    }
                    .nav-links a:hover { color: #fafafa; }
                    .hero {
                        max-width: 720px;
                        margin: 0 auto;
                        padding: 120px 24px 80px;
                        text-align: center;
                    }
                    .badge {
                        display: inline-flex;
                        align-items: center;
                        gap: 6px;
                        padding: 6px 12px;
                        background: rgba(255,255,255,0.05);
                        border: 1px solid rgba(255,255,255,0.1);
                        border-radius: 100px;
                        font-size: 13px;
                        color: #888;
                        margin-bottom: 24px;
                    }
                    .badge-dot {
                        width: 6px;
                        height: 6px;
                        background: #22c55e;
                        border-radius: 50%;
                    }
                    h1 {
                        font-size: 56px;
                        font-weight: 600;
                        letter-spacing: -0.03em;
                        line-height: 1.1;
                        margin-bottom: 20px;
                        background: linear-gradient(180deg, #fff 0%, #888 100%);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                    }
                    .tagline {
                        font-size: 18px;
                        color: #888;
                        line-height: 1.6;
                        margin-bottom: 40px;
                    }
                    .cta-group {
                        display: flex;
                        gap: 12px;
                        justify-content: center;
                        flex-wrap: wrap;
                    }
                    .btn {
                        display: inline-flex;
                        align-items: center;
                        gap: 8px;
                        padding: 12px 20px;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: 500;
                        text-decoration: none;
                        transition: all 0.15s;
                    }
                    .btn-primary {
                        background: #fafafa;
                        color: #0a0a0a;
                    }
                    .btn-primary:hover {
                        background: #e5e5e5;
                        transform: translateY(-1px);
                    }
                    .btn-secondary {
                        background: transparent;
                        color: #888;
                        border: 1px solid rgba(255,255,255,0.2);
                    }
                    .btn-secondary:hover {
                        color: #fafafa;
                        border-color: rgba(255,255,255,0.4);
                    }
                    .btn svg { width: 18px; height: 18px; }
                    .features {
                        max-width: 960px;
                        margin: 0 auto;
                        padding: 80px 24px;
                        display: grid;
                        grid-template-columns: repeat(3, 1fr);
                        gap: 1px;
                        background: rgba(255,255,255,0.1);
                        border-radius: 16px;
                        overflow: hidden;
                    }
                    .feature {
                        background: #0a0a0a;
                        padding: 32px;
                    }
                    .feature-icon {
                        width: 40px;
                        height: 40px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        background: rgba(255,255,255,0.05);
                        border-radius: 10px;
                        margin-bottom: 16px;
                        font-size: 18px;
                    }
                    .feature h3 {
                        font-size: 15px;
                        font-weight: 500;
                        margin-bottom: 8px;
                    }
                    .feature p {
                        font-size: 14px;
                        color: #666;
                        line-height: 1.5;
                    }
                    .footer {
                        padding: 40px 24px;
                        text-align: center;
                        color: #444;
                        font-size: 13px;
                        border-top: 1px solid rgba(255,255,255,0.05);
                    }
                    @media (max-width: 768px) {
                        .nav { padding: 16px 20px; }
                        .nav-links { display: none; }
                        .hero { padding: 80px 20px 60px; }
                        h1 { font-size: 36px; }
                        .features { grid-template-columns: 1fr; }
                    }
                </style>
            </head>
            <body>
                <nav class="nav">
                    <a href="/" class="nav-brand">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                        </svg>
                        Vibe Check
                    </a>
                    <div class="nav-links">
                        <a href="/health">Status</a>
                        <a href="/admin">Dashboard</a>
                        <a href="/slack/add">Install</a>
                    </div>
                </nav>

                <section class="hero">
                    <div class="badge">
                        <span class="badge-dot"></span>
                        Now available for Slack
                    </div>
                    <h1>Async standups that your team will actually enjoy</h1>
                    <p class="tagline">
                        Automated daily check-ins and Friday vibe checks.
                        Keep your team connected without the meeting fatigue.
                    </p>
                    <div class="cta-group">
                        <a href="/slack/add" class="btn btn-primary">
                            <svg viewBox="0 0 24 24" fill="currentColor">
                                <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"/>
                            </svg>
                            Add to Slack
                        </a>
                        <a href="/admin" class="btn btn-secondary">View Dashboard</a>
                    </div>
                </section>

                <section class="features">
                    <div class="feature">
                        <div class="feature-icon">📋</div>
                        <h3>Daily Standups</h3>
                        <p>Automated DMs at the time you choose. Responses collected and shared to your team channel.</p>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">✨</div>
                        <h3>Friday Vibe Checks</h3>
                        <p>Fun end-of-week check-ins with a more casual tone. See how your team is really feeling.</p>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">🌍</div>
                        <h3>Timezone Support</h3>
                        <p>Each team member gets messages at their local time. Perfect for distributed teams.</p>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">⚡</div>
                        <h3>Flexible Scheduling</h3>
                        <p>Daily standups, weekly check-ins, or both. Configure per person based on their role.</p>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">🔒</div>
                        <h3>Private by Default</h3>
                        <p>Responses go to a channel you control. Encrypted tokens and secure data handling.</p>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">📊</div>
                        <h3>Admin Dashboard</h3>
                        <p>Manage clients, view response history, and monitor scheduled jobs from one place.</p>
                    </div>
                </section>

                <footer class="footer">
                    Built for teams who value async communication
                </footer>
            </body>
        </html>
        """

    logger.info("Flask app configured")
    return flask_app
