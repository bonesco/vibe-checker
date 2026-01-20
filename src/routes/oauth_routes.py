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
        # Ensure URL has https:// prefix
        if not base_url.startswith('http://') and not base_url.startswith('https://'):
            base_url = f"https://{base_url}"
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
            # Ensure URL has https:// prefix
            if not base_url.startswith('http://') and not base_url.startswith('https://'):
                base_url = f"https://{base_url}"
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


# HTML Templates - Modern Linear/Vercel style
COMMON_STYLES = '''
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
            display: flex;
            flex-direction: column;
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
        .container {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 40px 24px;
        }
        .card {
            max-width: 480px;
            width: 100%;
        }
        .icon-wrapper {
            width: 48px;
            height: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 12px;
            margin-bottom: 24px;
        }
        .icon-error { background: rgba(239, 68, 68, 0.1); color: #ef4444; }
        .icon-success { background: rgba(34, 197, 94, 0.1); color: #22c55e; }
        h1 {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 12px;
            letter-spacing: -0.02em;
        }
        .subtitle {
            color: #888;
            font-size: 15px;
            line-height: 1.6;
            margin-bottom: 32px;
        }
        .error-box {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.2);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 24px;
            color: #fca5a5;
            font-size: 14px;
        }
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            transition: all 0.15s;
            width: 100%;
        }
        .btn-primary {
            background: #fafafa;
            color: #0a0a0a;
        }
        .btn-primary:hover {
            background: #e5e5e5;
        }
        .btn-secondary {
            background: transparent;
            color: #888;
            border: 1px solid rgba(255,255,255,0.2);
            margin-top: 12px;
        }
        .btn-secondary:hover {
            color: #fafafa;
            border-color: rgba(255,255,255,0.4);
        }
    </style>
'''

ERROR_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Installation Error - Vibe Check</title>
''' + COMMON_STYLES + '''
</head>
<body>
    <nav class="nav">
        <a href="/" class="nav-brand">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
            Vibe Check
        </a>
    </nav>
    <div class="container">
        <div class="card">
            <div class="icon-wrapper icon-error">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
                </svg>
            </div>
            <h1>Installation failed</h1>
            <p class="subtitle">Something went wrong during the OAuth flow.</p>
            <div class="error-box">{{ error }}</div>
            <a href="/slack/add" class="btn btn-primary">Try again</a>
            <a href="/" class="btn btn-secondary">Back to home</a>
        </div>
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
''' + COMMON_STYLES + '''
    <style>
        .team-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 100px;
            font-size: 14px;
            margin-bottom: 32px;
        }
        .steps {
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }
        .steps-title {
            font-size: 13px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 16px;
        }
        .step {
            display: flex;
            gap: 12px;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .step:last-child { border-bottom: none; }
        .step-num {
            width: 24px;
            height: 24px;
            background: rgba(255,255,255,0.1);
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 500;
            color: #888;
            flex-shrink: 0;
        }
        .step-text { font-size: 14px; color: #ccc; }
        .step-text code {
            background: rgba(255,255,255,0.1);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 13px;
        }
        .admin-note {
            font-size: 13px;
            color: #666;
            margin-bottom: 24px;
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
    </nav>
    <div class="container">
        <div class="card">
            <div class="icon-wrapper icon-success">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M20 6L9 17l-5-5"/>
                </svg>
            </div>
            <h1>Installation complete</h1>
            <p class="subtitle">Vibe Check has been added to your workspace.</p>
            <div class="team-badge">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" opacity="0.5">
                    <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52z"/>
                </svg>
                {{ team_name }}
            </div>

            <div class="steps">
                <div class="steps-title">Get started</div>
                <div class="step">
                    <span class="step-num">1</span>
                    <span class="step-text">Type <code>/vibe-help</code> to see all commands</span>
                </div>
                <div class="step">
                    <span class="step-num">2</span>
                    <span class="step-text">Set your channel with <code>/vibe-set-channel</code></span>
                </div>
                <div class="step">
                    <span class="step-num">3</span>
                    <span class="step-text">Add team members with <code>/vibe-add-client</code></span>
                </div>
                <div class="step">
                    <span class="step-num">4</span>
                    <span class="step-text">Test it with <code>/vibe-test</code></span>
                </div>
            </div>

            <p class="admin-note">You ({{ installer_id }}) are now an admin.</p>

            <a href="slack://open" class="btn btn-primary">Open Slack</a>
            <a href="/admin" class="btn btn-secondary">Go to Dashboard</a>
        </div>
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
''' + COMMON_STYLES + '''
    <style>
        .features {
            display: grid;
            gap: 1px;
            background: rgba(255,255,255,0.1);
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 32px;
        }
        .feature {
            background: #0a0a0a;
            padding: 20px;
            display: flex;
            gap: 16px;
            align-items: flex-start;
        }
        .feature-icon {
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            flex-shrink: 0;
        }
        .feature-text h3 {
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 4px;
        }
        .feature-text p {
            font-size: 13px;
            color: #666;
            line-height: 1.4;
        }
        .scopes {
            font-size: 12px;
            color: #666;
            margin-top: 24px;
        }
        .scopes summary {
            cursor: pointer;
            color: #888;
        }
        .scopes ul {
            margin-top: 8px;
            padding-left: 20px;
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
    </nav>
    <div class="container">
        <div class="card">
            <h1>Add to Slack</h1>
            <p class="subtitle">Connect Vibe Check to your Slack workspace to start running async standups and vibe checks.</p>

            <div class="features">
                <div class="feature">
                    <div class="feature-icon">📋</div>
                    <div class="feature-text">
                        <h3>Daily standups</h3>
                        <p>Automated DMs at the time you choose</p>
                    </div>
                </div>
                <div class="feature">
                    <div class="feature-icon">✨</div>
                    <div class="feature-text">
                        <h3>Friday vibe checks</h3>
                        <p>Fun end-of-week pulse on team morale</p>
                    </div>
                </div>
                <div class="feature">
                    <div class="feature-icon">🔒</div>
                    <div class="feature-text">
                        <h3>Private & secure</h3>
                        <p>Data encrypted, you control the channel</p>
                    </div>
                </div>
            </div>

            <a href="/slack/install" class="btn btn-primary">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"/>
                </svg>
                Continue with Slack
            </a>
            <a href="/" class="btn btn-secondary">Learn more</a>

            <details class="scopes">
                <summary>Permissions requested</summary>
                <ul>
                    <li>Send messages as Vibe Check</li>
                    <li>Send direct messages to users</li>
                    <li>View basic user info</li>
                    <li>Access channels you select</li>
                </ul>
            </details>
        </div>
    </div>
</body>
</html>
'''
