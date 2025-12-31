#!/usr/bin/env python3
"""
Vibe Check Slack App - Main Entry Point

Professional client communication app with daily standups and weekly feedback collection
"""

import os
import sys
import traceback
from flask import Flask, jsonify

# Create a minimal Flask app first (so health checks work even if main app fails)
flask_app = Flask(__name__)

@flask_app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@flask_app.route("/", methods=["GET"])
def home():
    return "<h1>Vibe Check</h1><p>App is starting...</p>"

def init_full_app():
    """Initialize the full Slack app"""
    global flask_app

    try:
        print("=" * 50, flush=True)
        print("Starting Vibe Check Slack App...", flush=True)
        print("=" * 50, flush=True)

        # Import after basic Flask app is created
        from src.config import config, validate_environment
        from src.utils.logger import setup_logger
        from src.app_factory import create_slack_app, create_flask_app
        from src.database.session import init_db

        logger = setup_logger(__name__)

        # Validate environment configuration
        print("Validating environment...", flush=True)
        if not validate_environment():
            print("ERROR: Environment validation failed!", flush=True)
            return

        # Debug: Check if bot token is set
        bot_token = config.SLACK_BOT_TOKEN
        print(f"SLACK_BOT_TOKEN set: {bool(bot_token)}", flush=True)
        if bot_token:
            print(f"SLACK_BOT_TOKEN starts with: {bot_token[:10]}...", flush=True)

        # Initialize database
        print("Initializing database...", flush=True)
        init_db()

        # Create Slack Bolt app
        print("Creating Slack app...", flush=True)
        slack_app = create_slack_app()

        # Register handlers
        print("Registering handlers...", flush=True)
        from src.handlers import commands, actions, views, events
        commands.register(slack_app)
        actions.register(slack_app)
        views.register(slack_app)
        events.register(slack_app)

        # Initialize scheduler
        print("Initializing scheduler...", flush=True)
        from src.services.scheduler_service import init_scheduler
        init_scheduler()

        # Replace with full Flask app
        print("Creating full Flask app...", flush=True)
        flask_app = create_flask_app(slack_app)

        print("=" * 50, flush=True)
        print(f"Vibe Check is ready!", flush=True)
        print("=" * 50, flush=True)

    except Exception as e:
        print(f"ERROR during initialization: {e}", flush=True)
        print(traceback.format_exc(), flush=True)
        # Keep the minimal flask_app running so health checks pass

# Initialize on import
init_full_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host="0.0.0.0", port=port, debug=False)
