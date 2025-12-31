"""Slack Bolt app factory with OAuth support"""

from slack_bolt import App
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, jsonify
from src.config import config
from src.utils.logger import setup_logger
from src.services.workspace_service import create_workspace, get_workspace_by_team_id, get_bot_token
from src.utils.encryption import decrypt_token

logger = setup_logger(__name__)


# Custom installation store that uses our database
class DatabaseInstallationStore:
    """Store Slack installations in PostgreSQL database"""

    def save(self, installation):
        """Save installation to database"""
        try:
            create_workspace(
                team_id=installation.team_id,
                team_name=installation.team_name or installation.team_id,
                bot_token=installation.bot_token,
                bot_user_id=installation.bot_user_id,
                scope=installation.bot_scopes,
                installer_user_id=installation.user_id
            )
            logger.info(f"Saved installation for team: {installation.team_id}")
        except Exception as e:
            logger.error(f"Failed to save installation: {e}")
            raise

    def find(self, *, enterprise_id: str = None, team_id: str, user_id: str = None):
        """Find installation from database"""
        try:
            workspace = get_workspace_by_team_id(team_id)
            if not workspace:
                return None

            # Return installation object
            from slack_bolt.oauth.installation_store import Installation, Bot

            bot = Bot(
                app_id=None,  # Not needed for our use case
                enterprise_id=enterprise_id,
                team_id=team_id,
                bot_token=decrypt_token(workspace.bot_token),
                bot_id=workspace.bot_user_id,
                bot_user_id=workspace.bot_user_id,
                bot_scopes=workspace.scope.split(','),
                installed_at=workspace.created_at
            )

            installation = Installation(
                app_id=None,
                enterprise_id=enterprise_id,
                team_id=team_id,
                bot_token=decrypt_token(workspace.bot_token),
                bot_id=workspace.bot_user_id,
                bot_user_id=workspace.bot_user_id,
                bot_scopes=workspace.scope.split(','),
                user_id=user_id or (workspace.admin_user_ids[0] if workspace.admin_user_ids else None),
                installed_at=workspace.created_at
            )

            return installation

        except Exception as e:
            logger.error(f"Failed to find installation: {e}")
            return None


def create_slack_app() -> App:
    """
    Create and configure Slack Bolt app

    Uses bot token directly if SLACK_BOT_TOKEN is set (single-workspace mode),
    otherwise uses OAuth for multi-workspace support.

    Returns:
        Configured Slack Bolt App instance
    """
    import os

    # Check if we have a direct bot token (single-workspace mode)
    bot_token = config.SLACK_BOT_TOKEN
    if bot_token:
        logger.info("Creating Slack app in single-workspace mode (using bot token)")

        # Remove from env so Slack Bolt doesn't try to use it in OAuth mode
        if 'SLACK_BOT_TOKEN' in os.environ:
            del os.environ['SLACK_BOT_TOKEN']

        app = App(
            token=bot_token,
            signing_secret=config.SLACK_SIGNING_SECRET
        )
        return app

    # Otherwise use OAuth for multi-workspace support
    logger.info("Creating Slack app with OAuth support")
    oauth_settings = OAuthSettings(
        client_id=config.SLACK_CLIENT_ID,
        client_secret=config.SLACK_CLIENT_SECRET,
        scopes=[
            "chat:write",
            "im:write",
            "im:history",
            "users:read",
            "users:read.email",
            "channels:read",
            "channels:manage",
            "channels:join",
            "commands",
            "team:read"
        ],
        installation_store=DatabaseInstallationStore()
    )

    app = App(
        signing_secret=config.SLACK_SIGNING_SECRET,
        oauth_settings=oauth_settings
    )

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

    @flask_app.route("/slack/install", methods=["GET"])
    def slack_install():
        """Initiate OAuth installation flow"""
        return handler.handle(request)

    @flask_app.route("/slack/oauth_redirect", methods=["GET"])
    def slack_oauth_redirect():
        """Handle OAuth callback"""
        return handler.handle(request)

    @flask_app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint for Railway"""
        return jsonify({"status": "ok"}), 200

    @flask_app.route("/", methods=["GET"])
    def home():
        """Home page with installation link"""
        install_url = f"/slack/install"
        return f"""
        <html>
            <head>
                <title>Vibe Check - Client Communication App</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                        max-width: 600px;
                        margin: 100px auto;
                        padding: 20px;
                        text-align: center;
                    }}
                    h1 {{ color: #333; }}
                    p {{ color: #666; line-height: 1.6; }}
                    .install-btn {{
                        display: inline-block;
                        margin-top: 20px;
                        padding: 12px 24px;
                        background: #4A154B;
                        color: white;
                        text-decoration: none;
                        border-radius: 4px;
                        font-weight: bold;
                    }}
                    .install-btn:hover {{ background: #611f69; }}
                </style>
            </head>
            <body>
                <h1>📋 Vibe Check</h1>
                <p>Professional client communication with daily standups and weekly feedback collection.</p>
                <p>Install this app to your Slack workspace to get started.</p>
                <a href="{install_url}" class="install-btn">Add to Slack</a>
            </body>
        </html>
        """

    logger.info("Flask app configured")
    return flask_app
