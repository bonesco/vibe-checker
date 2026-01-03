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
        return handler.handle(request)

    @flask_app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint for Railway"""
        return jsonify({"status": "ok"}), 200

    @flask_app.route("/", methods=["GET"])
    def home():
        """Home page"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VIBE CHECK</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
            background: #fff;
            color: #000;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 2rem;
        }
        .container {
            max-width: 480px;
            margin: 0 auto;
        }
        h1 {
            font-size: 2.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 2rem;
            line-height: 1;
        }
        .status {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #000;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .status::before {
            content: '';
            width: 6px;
            height: 6px;
            background: #000;
            display: inline-block;
        }
        .divider {
            width: 100%;
            height: 1px;
            background: #000;
            margin: 2rem 0;
        }
        .command {
            font-size: 0.875rem;
            color: #666;
        }
        .command code {
            background: #f5f5f5;
            padding: 0.25rem 0.5rem;
            border: 1px solid #e0e0e0;
        }
    </style>
</head>
<body>
    <div class="container">
        <p class="status">System Active</p>
        <h1>VIBE CHECK</h1>
        <div class="divider"></div>
        <p class="command">Run <code>/vibe-help</code> in Slack</p>
    </div>
</body>
</html>"""

    logger.info("Flask app configured")
    return flask_app
