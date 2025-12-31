#!/usr/bin/env python3
"""
Vibe Check Slack App - Main Entry Point
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

        # Import dependencies
        from src.config import config, validate_environment
        from src.app_factory import create_slack_app, create_flask_app
        from src.database.session import init_db

        # Validate environment
        print("Validating environment...", flush=True)
        if not validate_environment():
            print("ERROR: Environment validation failed!", flush=True)
            return

        # Check bot token
        if not config.SLACK_BOT_TOKEN:
            print("ERROR: SLACK_BOT_TOKEN is required!", flush=True)
            return

        print(f"Bot token configured: {config.SLACK_BOT_TOKEN[:15]}...", flush=True)

        # Initialize database
        print("Initializing database...", flush=True)
        init_db()

        # Bootstrap workspace for single-workspace mode
        print("Setting up workspace...", flush=True)
        from slack_sdk import WebClient
        from src.services.workspace_service import get_workspace_by_team_id, create_workspace

        slack_client = WebClient(token=config.SLACK_BOT_TOKEN)
        auth_info = slack_client.auth_test()
        team_id = auth_info["team_id"]
        team_name = auth_info.get("team", "Workspace")
        bot_user_id = auth_info["user_id"]

        print(f"Connected to: {team_name} ({team_id})", flush=True)

        # Create workspace if it doesn't exist
        if not get_workspace_by_team_id(team_id):
            print("Creating workspace record...", flush=True)
            create_workspace(
                team_id=team_id,
                team_name=team_name,
                bot_token=config.SLACK_BOT_TOKEN,
                bot_user_id=bot_user_id,
                scope="chat:write,commands,im:write,users:read",
                installer_user_id=bot_user_id
            )
        else:
            print("Workspace already exists.", flush=True)

        # Create Slack app
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
        print("Starting scheduler...", flush=True)
        from src.services.scheduler_service import init_scheduler
        init_scheduler()

        # Create Flask app
        print("Creating Flask app...", flush=True)
        flask_app = create_flask_app(slack_app)

        print("=" * 50, flush=True)
        print("Vibe Check is ready!", flush=True)
        print("=" * 50, flush=True)

    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        print(traceback.format_exc(), flush=True)


# Initialize on import
init_full_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host="0.0.0.0", port=port, debug=False)
