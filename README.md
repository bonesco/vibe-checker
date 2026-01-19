# Vibe Check - Client Communication Slack App

Professional Slack app for managing client relationships through automated daily standups and weekly feedback collection.

## Features

- **Daily Standups**: Automated DM standup requests (daily or Monday-only)
- **Weekly Feedback**: Friday feedback collection with satisfaction ratings
- **Private & Secure**: All responses are private until posted to your vibe check channel
- **Admin Controls**: Role-based access for managing clients and settings
- **Web Admin Dashboard**: Browser-based dashboard for analytics and management
- **Multi-Workspace Support**: OAuth-based installation for distribution
- **Data Retention**: Automatic cleanup of old data (configurable)
- **Health Monitoring**: Built-in health check endpoint for monitoring
- **Rate Limiting**: Production-ready with built-in rate limiting
- **Security Headers**: HSTS, CSP, and other security headers enabled

## Quick Start

### 1. Deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app)

1. Click the button above or go to [Railway](https://railway.app)
2. Connect your GitHub repository
3. Add a PostgreSQL database
4. Set environment variables (see below)
5. Deploy

### 2. Configure Environment Variables

**Required:**

| Variable | Description |
|----------|-------------|
| `SLACK_BOT_TOKEN` | Bot token from Slack app (starts with `xoxb-`) |
| `SLACK_SIGNING_SECRET` | Signing secret from Slack app Basic Information |
| `DATABASE_URL` | PostgreSQL connection string (auto-set by Railway) |
| `ENCRYPTION_KEY` | Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

**For OAuth/Multi-Workspace (Optional):**

| Variable | Description |
|----------|-------------|
| `SLACK_CLIENT_ID` | Client ID from Slack app (for OAuth installation) |
| `SLACK_CLIENT_SECRET` | Client Secret from Slack app (for OAuth installation) |

**For Admin Dashboard (Optional):**

| Variable | Description |
|----------|-------------|
| `ADMIN_DASHBOARD_SECRET` | Password for web admin dashboard at `/admin` |
| `FLASK_SECRET_KEY` | Session encryption key (auto-generated if not set) |

**Other Optional:**

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_USER_ID` | - | Your Slack user ID to set as initial admin |
| `APP_URL` | - | Public URL of your app (for OAuth redirects) |
| `PORT` | 8000 | Server port |
| `LOG_LEVEL` | INFO | Logging level |
| `DATA_RETENTION_DAYS` | 90 | Days to keep response data |

### 3. Create Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app
2. Use the manifest from `docs/slack_manifest.json` OR configure manually:

**Bot Token Scopes** (OAuth & Permissions):
- `chat:write` - Send messages
- `commands` - Handle slash commands
- `im:write` - Send DMs
- `users:read` - Get user info

**Slash Commands** (all use Request URL: `https://YOUR-APP-URL/slack/events`):
- `/vibe-add-client` - Add a new client
- `/vibe-remove-client` - Remove a client
- `/vibe-list-clients` - List all clients
- `/vibe-pause` - Pause standups
- `/vibe-resume` - Resume standups
- `/vibe-set-channel` - Set feedback channel
- `/vibe-admin` - Manage admins
- `/vibe-test` - Send test standup
- `/vibe-help` - Show help

**Interactivity** (same Request URL):
- Enable Interactivity
- Request URL: `https://YOUR-APP-URL/slack/events`

### 4. Install to Workspace

1. Go to Install App in your Slack app settings
2. Install to your workspace
3. Copy the Bot Token to your environment variables

### 5. Set Up Admin

Add your Slack user ID as `ADMIN_USER_ID` environment variable, then redeploy.

To find your user ID: Go to your Slack profile > More > Copy member ID

## Usage

### Admin Commands

| Command | Description |
|---------|-------------|
| `/vibe-add-client` | Add a user to receive daily standups |
| `/vibe-remove-client` | Remove a client |
| `/vibe-list-clients` | View all clients and their status |
| `/vibe-pause` | Pause standups for a client |
| `/vibe-resume` | Resume paused standups |
| `/vibe-set-channel` | Set the feedback channel |
| `/vibe-admin` | View/manage workspace admins |
| `/vibe-test` | Send a test standup to yourself |
| `/vibe-help` | Show help documentation |

### Workflow

1. **Add clients** using `/vibe-add-client`
2. **Set the feedback channel** using `/vibe-set-channel`
3. Clients receive automated **standup DMs** at their scheduled time
4. Clients receive **weekly feedback requests** on Fridays
5. All feedback is posted to your private **vibe check channel**

## Architecture

```
vibe-checker/
├── app.py                      # Main entry point
├── requirements.txt            # Python dependencies
├── Procfile                    # Railway deployment
├── src/
│   ├── config.py               # Configuration
│   ├── app_factory.py          # Slack Bolt setup
│   ├── models/                 # Database models
│   ├── services/               # Business logic
│   ├── handlers/               # Slack event handlers
│   ├── blocks/                 # Block Kit UI
│   ├── middleware/             # Auth & error handling
│   └── utils/                  # Utilities
└── docs/                       # Documentation
```

## Admin Dashboard

The app includes a web-based admin dashboard at `/admin` for managing your installation.

### Features:
- **Dashboard**: Overview of clients, responses, and scheduler status
- **Client Management**: View, pause, resume, and delete clients
- **Analytics**: Response metrics and satisfaction trends
- **Scheduled Jobs**: Monitor APScheduler jobs
- **Settings**: View workspace configuration

### Enabling the Dashboard:
Set the `ADMIN_DASHBOARD_SECRET` environment variable to enable authentication:

```bash
ADMIN_DASHBOARD_SECRET=your-secure-password-here
```

Then access `https://your-app-url/admin` and log in with your password.

## Multi-Workspace Distribution

To allow other workspaces to install your app via OAuth:

### 1. Configure OAuth in Slack App Settings:

1. Go to **OAuth & Permissions** in your Slack app
2. Add a Redirect URL: `https://your-app-url/slack/oauth_redirect`
3. Copy the **Client ID** and **Client Secret**

### 2. Set Environment Variables:

```bash
SLACK_CLIENT_ID=your-client-id
SLACK_CLIENT_SECRET=your-client-secret
APP_URL=https://your-app-url
```

### 3. Share Installation Link:

Users can install your app at: `https://your-app-url/slack/add`

Or use the "Add to Slack" button that appears on your homepage.

## Health Check

The app exposes a health endpoint at `/health` that returns:

```json
{
  "status": "ok",
  "app": "running",
  "database": "connected",
  "scheduler": "running",
  "scheduled_jobs": 5
}
```

Use this for monitoring and load balancer health checks.

## Security

- Bot tokens encrypted at rest using Fernet
- Request signature verification for all Slack requests
- Role-based admin access for commands
- Automatic data retention cleanup
- No sensitive data logged

## Data Retention

By default, standup and feedback responses older than 90 days are automatically deleted.
Configure with `DATA_RETENTION_DAYS` environment variable.

Cleanup runs weekly on Sundays at 2:00 AM UTC.

## Troubleshooting

### "You don't have permission" error

1. Ensure `ADMIN_USER_ID` is set to your Slack user ID
2. Redeploy the app
3. Check logs for "Successfully added X as admin"

### Commands not working

1. Verify all slash command URLs in Slack app settings
2. Check that Interactivity Request URL is set
3. Ensure bot is in channels where you're using commands

### Check logs

Railway: Dashboard > Select service > View Logs

Look for:
- `Vibe Check is ready!` - App started successfully
- `ADMIN_USER_ID env var:` - Admin configuration
- Error messages with stack traces

## Local Development

```bash
# Clone and setup
git clone <repo-url>
cd vibe-checker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your values

# Run with ngrok for Slack webhooks
ngrok http 8000
# Update Slack app URLs with ngrok URL

# Start app
python app.py
```

## License

MIT License - See LICENSE file for details.

---

Built with Slack Bolt for Python
