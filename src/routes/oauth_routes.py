"""OAuth routes for Slack app installation"""

import os
from flask import Blueprint, redirect, request, url_for, render_template_string
from slack_sdk.oauth import AuthorizeUrlGenerator
from slack_sdk.oauth.installation_store import Installation
from slack_sdk.web import WebClient
from src.config import config
from src.services.workspace_service import create_workspace, get_workspace_by_team_id
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

oauth_bp = Blueprint('oauth', __name__, url_prefix='/slack')

# Required OAuth scopes for the bot
BOT_SCOPES = [
    "chat:write",
    "commands",
    "im:write",
    "im:history",
    "users:read",
    "users:read.email",
    "channels:read",
    "groups:read",
]

# User scopes (optional, for enhanced features)
USER_SCOPES = []


def get_oauth_settings():
    """Get OAuth settings from config"""
    return {
        'client_id': config.SLACK_CLIENT_ID,
        'client_secret': config.SLACK_CLIENT_SECRET,
        'scopes': BOT_SCOPES,
        'user_scopes': USER_SCOPES,
    }


@oauth_bp.route('/install')
def install():
    """
    Initiate OAuth installation flow.

    Redirects to Slack's authorization page.
    """
    settings = get_oauth_settings()

    if not settings['client_id']:
        return render_template_string(ERROR_TEMPLATE,
            error="OAuth not configured. Missing SLACK_CLIENT_ID.")

    # Get the callback URL
    # Use RAILWAY_STATIC_URL if available, otherwise build from request
    base_url = os.environ.get('RAILWAY_STATIC_URL') or os.environ.get('APP_URL')
    if base_url:
        redirect_uri = f"{base_url.rstrip('/')}/slack/oauth_redirect"
    else:
        redirect_uri = url_for('oauth.oauth_callback', _external=True)

    # Build the OAuth URL with redirect_uri in constructor
    authorize_url_generator = AuthorizeUrlGenerator(
        client_id=settings['client_id'],
        scopes=settings['scopes'],
        user_scopes=settings['user_scopes'],
        redirect_uri=redirect_uri,
    )

    # Generate authorization URL with state for CSRF protection
    import secrets
    state = secrets.token_urlsafe(32)

    # In production, you'd store this state in a session or database
    # For simplicity, we'll skip state validation but include it

    auth_url = authorize_url_generator.generate(state=state)

    logger.info(f"Redirecting to OAuth with redirect_uri: {redirect_uri}")
    return redirect(auth_url)


@oauth_bp.route('/oauth_redirect')
def oauth_callback():
    """
    Handle OAuth callback from Slack.

    Exchanges the authorization code for tokens and creates the workspace.
    """
    settings = get_oauth_settings()

    # Check for errors
    error = request.args.get('error')
    if error:
        error_description = request.args.get('error_description', 'Unknown error')
        logger.error(f"OAuth error: {error} - {error_description}")
        return render_template_string(ERROR_TEMPLATE,
            error=f"Installation failed: {error_description}")

    # Get the authorization code
    code = request.args.get('code')
    if not code:
        return render_template_string(ERROR_TEMPLATE,
            error="No authorization code received")

    try:
        # Exchange code for tokens
        client = WebClient()

        # Get the redirect URI (must match what was used in install)
        base_url = os.environ.get('RAILWAY_STATIC_URL') or os.environ.get('APP_URL')
        if base_url:
            redirect_uri = f"{base_url.rstrip('/')}/slack/oauth_redirect"
        else:
            redirect_uri = url_for('oauth.oauth_callback', _external=True)

        oauth_response = client.oauth_v2_access(
            client_id=settings['client_id'],
            client_secret=settings['client_secret'],
            code=code,
            redirect_uri=redirect_uri
        )

        # Extract installation data
        team_id = oauth_response['team']['id']
        team_name = oauth_response['team']['name']
        bot_token = oauth_response['access_token']
        bot_user_id = oauth_response['bot_user_id']
        scope = oauth_response.get('scope', ','.join(BOT_SCOPES))
        installer_user_id = oauth_response.get('authed_user', {}).get('id', bot_user_id)

        logger.info(f"OAuth successful for team: {team_name} ({team_id})")

        # Create or update workspace
        workspace = create_workspace(
            team_id=team_id,
            team_name=team_name,
            bot_token=bot_token,
            bot_user_id=bot_user_id,
            scope=scope,
            installer_user_id=installer_user_id
        )

        logger.info(f"Workspace created/updated: {workspace.id}")

        # Show success page
        return render_template_string(SUCCESS_TEMPLATE,
            team_name=team_name,
            installer_id=installer_user_id)

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return render_template_string(ERROR_TEMPLATE,
            error=f"Installation failed: {str(e)}")


@oauth_bp.route('/add')
def add_to_slack():
    """
    Landing page with Add to Slack button.

    This page can be linked from documentation or shared publicly.
    """
    settings = get_oauth_settings()

    if not settings['client_id']:
        return render_template_string(ERROR_TEMPLATE,
            error="OAuth not configured. Set SLACK_CLIENT_ID environment variable.")

    return render_template_string(ADD_TO_SLACK_TEMPLATE,
        client_id=settings['client_id'],
        scopes=','.join(settings['scopes']))


# HTML Templates
ERROR_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Installation Error - Vibe Check</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .card {
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 500px;
            text-align: center;
        }
        h1 { color: #dc3545; margin-bottom: 16px; }
        p { color: #666; line-height: 1.6; }
        .error-box {
            background: #fee;
            border: 1px solid #fcc;
            border-radius: 8px;
            padding: 16px;
            margin: 20px 0;
            color: #c00;
        }
        a {
            display: inline-block;
            margin-top: 20px;
            padding: 12px 24px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 8px;
        }
        a:hover { background: #5a6fd6; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Installation Error</h1>
        <div class="error-box">{{ error }}</div>
        <p>Please try again or contact support if the issue persists.</p>
        <a href="/slack/add">Try Again</a>
    </div>
</body>
</html>
'''

SUCCESS_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Installation Complete - Vibe Check</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .card {
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            text-align: center;
        }
        .success-icon {
            width: 80px;
            height: 80px;
            background: #28a745;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 24px;
        }
        .success-icon svg {
            width: 40px;
            height: 40px;
            fill: white;
        }
        h1 { color: #333; margin-bottom: 16px; }
        p { color: #666; line-height: 1.6; margin-bottom: 12px; }
        .team-name {
            font-size: 24px;
            color: #667eea;
            font-weight: 600;
            margin: 16px 0;
        }
        .steps {
            text-align: left;
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin: 24px 0;
        }
        .steps h3 { margin-bottom: 12px; color: #333; }
        .steps ol { padding-left: 20px; }
        .steps li { margin: 8px 0; color: #555; }
        .steps code {
            background: #e9ecef;
            padding: 2px 6px;
            border-radius: 4px;
        }
        a.btn {
            display: inline-block;
            padding: 14px 28px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            margin-top: 16px;
        }
        a.btn:hover { background: #5a6fd6; }
    </style>
</head>
<body>
    <div class="card">
        <div class="success-icon">
            <svg viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
        </div>
        <h1>Installation Complete!</h1>
        <p>Vibe Check has been installed to</p>
        <div class="team-name">{{ team_name }}</div>

        <div class="steps">
            <h3>Next Steps</h3>
            <ol>
                <li>Go to Slack and type <code>/vibe-help</code> to see all commands</li>
                <li>Set up your feedback channel with <code>/vibe-set-channel</code></li>
                <li>Add your first client with <code>/vibe-add-client</code></li>
                <li>Test it out with <code>/vibe-test</code></li>
            </ol>
        </div>

        <p style="font-size: 14px; color: #888;">
            You (<code>{{ installer_id }}</code>) are now an admin for this installation.
        </p>

        <a href="https://slack.com/app_redirect?app=vibe-check" class="btn">Open in Slack</a>
    </div>
</body>
</html>
'''

ADD_TO_SLACK_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Install Vibe Check for Slack</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .card {
            background: white;
            border-radius: 16px;
            padding: 50px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            text-align: center;
        }
        h1 {
            color: #333;
            margin-bottom: 12px;
            font-size: 36px;
        }
        .tagline {
            color: #666;
            font-size: 18px;
            margin-bottom: 30px;
        }
        .features {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            text-align: left;
            margin: 30px 0;
        }
        .feature {
            padding: 16px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .feature h3 {
            color: #333;
            font-size: 16px;
            margin-bottom: 6px;
        }
        .feature p {
            color: #666;
            font-size: 14px;
        }
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
            margin-top: 20px;
            transition: background 0.2s;
        }
        .slack-btn:hover {
            background: #611f69;
        }
        .slack-btn svg {
            width: 24px;
            height: 24px;
            margin-right: 12px;
        }
        .privacy {
            margin-top: 24px;
            font-size: 13px;
            color: #888;
        }
        .privacy a {
            color: #667eea;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>Vibe Check</h1>
        <p class="tagline">Automated standups and feedback collection for Slack</p>

        <div class="features">
            <div class="feature">
                <h3>Daily Standups</h3>
                <p>Automated DMs to collect progress updates from your team</p>
            </div>
            <div class="feature">
                <h3>Weekly Feedback</h3>
                <p>Friday check-ins to understand how your team is feeling</p>
            </div>
            <div class="feature">
                <h3>Flexible Scheduling</h3>
                <p>Configure timing per person with timezone support</p>
            </div>
            <div class="feature">
                <h3>Private by Design</h3>
                <p>Responses go to a private channel you control</p>
            </div>
        </div>

        <a href="/slack/install" class="slack-btn">
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"/>
            </svg>
            Add to Slack
        </a>

        <p class="privacy">
            By installing, you agree to our <a href="#">Terms of Service</a> and <a href="#">Privacy Policy</a>
        </p>
    </div>
</body>
</html>
'''
