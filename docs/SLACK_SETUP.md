# 🔧 Slack App Setup Guide

Complete guide to creating and configuring your Vibe Check Slack app.

## Prerequisites

- Slack workspace with admin permissions
- Deployed Vibe Check app with public URL (see [DEPLOYMENT.md](DEPLOYMENT.md))

## Step 1: Create Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)

2. Click **"Create New App"**

3. Choose **"From an app manifest"**

4. Select your workspace

5. Paste the manifest from `docs/slack_manifest.json` (see below)

6. Review permissions and click **"Create"**

**Alternative**: Create from scratch following steps below

---

## Step 2: Basic Information

1. In your app dashboard → **Basic Information**

2. **App Name**: Vibe Check

3. **Short Description**: "Client communication with daily standups and weekly feedback"

4. **App Icon**: Upload a custom icon (optional)

5. **Background Color**: `#2c2d30`

---

## Step 3: OAuth & Permissions

### Bot Token Scopes

Go to **OAuth & Permissions** → **Scopes** → **Bot Token Scopes**, add:

| Scope | Purpose |
|-------|---------|
| `chat:write` | Send messages |
| `im:write` | Send DMs |
| `im:history` | Read DM history |
| `users:read` | Get user information |
| `users:read.email` | Get user emails |
| `channels:read` | Read channel info |
| `channels:manage` | Manage vibe check channel |
| `channels:join` | Join channels |
| `commands` | Slash commands |
| `team:read` | Get workspace info |

### Redirect URLs

In **OAuth & Permissions** → **Redirect URLs**, add:

```
https://your-app.railway.app/slack/oauth_redirect
```

Replace `your-app.railway.app` with your actual deployment URL.

---

## Step 4: Slash Commands

Go to **Slash Commands** and create these commands:

### /vibe-add-client
- **Command**: `/vibe-add-client`
- **Request URL**: `https://your-app.railway.app/slack/events`
- **Short Description**: "Add a new client to receive standups"
- **Usage Hint**: (leave empty)

### /vibe-remove-client
- **Command**: `/vibe-remove-client`
- **Request URL**: `https://your-app.railway.app/slack/events`
- **Short Description**: "Remove a client from receiving standups"
- **Usage Hint**: `@user`

### /vibe-list-clients
- **Command**: `/vibe-list-clients`
- **Request URL**: `https://your-app.railway.app/slack/events`
- **Short Description**: "List all active clients"
- **Usage Hint**: (leave empty)

### /vibe-pause
- **Command**: `/vibe-pause`
- **Request URL**: `https://your-app.railway.app/slack/events`
- **Short Description**: "Pause standups for a client"
- **Usage Hint**: `@user`

### /vibe-resume
- **Command**: `/vibe-resume`
- **Request URL**: `https://your-app.railway.app/slack/events`
- **Short Description**: "Resume standups for a client"
- **Usage Hint**: `@user`

### /vibe-test
- **Command**: `/vibe-test`
- **Request URL**: `https://your-app.railway.app/slack/events`
- **Short Description**: "Send a test standup to yourself"
- **Usage Hint**: (leave empty)

### /vibe-help
- **Command**: `/vibe-help`
- **Request URL**: `https://your-app.railway.app/slack/events`
- **Short Description**: "Show help documentation"
- **Usage Hint**: (leave empty)

---

## Step 5: Interactivity

Go to **Interactivity & Shortcuts**:

1. **Turn On Interactivity**

2. **Request URL**: `https://your-app.railway.app/slack/events`

3. Click **"Save Changes"**

---

## Step 6: Event Subscriptions

Go to **Event Subscriptions**:

1. **Enable Events**: Toggle ON

2. **Request URL**: `https://your-app.railway.app/slack/events`

3. Wait for URL verification (green checkmark)

### Subscribe to Bot Events

Add these bot events:

- `app_home_opened` - When user opens app home
- `team_join` - When new member joins workspace

4. Click **"Save Changes"**

---

## Step 7: App Home

Go to **App Home**:

1. **Display Name**: "Vibe Check"

2. **Default Name**: "vibecheck"

3. **Always Show My Bot as Online**: Toggle ON

4. **Home Tab**: Enable (optional, for future features)

5. **Messages Tab**: Enable

6. Click **"Save"**

---

## Step 8: Get Credentials

Go to **Basic Information** → **App Credentials**:

Copy these values to your `.env` or Railway environment variables:

```bash
SLACK_CLIENT_ID=<Client ID>
SLACK_CLIENT_SECRET=<Client Secret>
SLACK_SIGNING_SECRET=<Signing Secret>
```

---

## Step 9: Install App to Workspace

### Option A: Install Directly

1. Go to **Install App**

2. Click **"Install to Workspace"**

3. Review permissions

4. Click **"Allow"**

### Option B: Shareable Install Link

1. Go to **Manage Distribution**

2. **Activate Public Distribution** (if sharing with other workspaces)

3. Copy **"Shareable URL"** or go to your app homepage:
   ```
   https://your-app.railway.app/
   ```

4. Click **"Add to Slack"**

---

## Step 10: Configure Vibe Check Channel

After installation:

1. **Create a private channel** for feedback:
   ```
   /create #vibe-check-private
   ```

2. **Invite the bot**:
   ```
   /invite @Vibe Check
   ```

3. **Note the channel** - feedback will be posted here

---

## Testing the Installation

### Test OAuth Flow

1. Visit: `https://your-app.railway.app/`

2. Click **"Add to Slack"**

3. Authorize the app

4. Verify successful installation in logs

### Test Health Check

```bash
curl https://your-app.railway.app/health
```

Should return:
```json
{
  "status": "healthy",
  "database": "connected",
  "scheduler": "running"
}
```

### Test Commands

In Slack:

1. **Show help**:
   ```
   /vibe-help
   ```

2. **Test standup**:
   ```
   /vibe-test
   ```
   Check your DMs for a test standup message

3. **List clients** (should be empty initially):
   ```
   /vibe-list-clients
   ```

### Add Your First Client

1. Run:
   ```
   /vibe-add-client
   ```

2. Fill out the modal:
   - **Client User**: Select a user
   - **Timezone**: Choose timezone
   - **Schedule**: Daily or Monday-only
   - **Time**: When to send standups

3. Click **"Add Client"**

4. Verify in logs that client was added and jobs scheduled

---

## Slack App Manifest

Save this as `docs/slack_manifest.json` for easy app creation:

```json
{
  "display_information": {
    "name": "Vibe Check",
    "description": "Daily standups and weekly feedback collection for client relationships",
    "background_color": "#2c2d30"
  },
  "features": {
    "bot_user": {
      "display_name": "Vibe Check",
      "always_online": true
    },
    "slash_commands": [
      {
        "command": "/vibe-add-client",
        "description": "Add a new client to receive standups",
        "usage_hint": ""
      },
      {
        "command": "/vibe-remove-client",
        "description": "Remove a client",
        "usage_hint": "@user"
      },
      {
        "command": "/vibe-list-clients",
        "description": "List all active clients",
        "usage_hint": ""
      },
      {
        "command": "/vibe-pause",
        "description": "Pause standups for a client",
        "usage_hint": "@user"
      },
      {
        "command": "/vibe-resume",
        "description": "Resume standups",
        "usage_hint": "@user"
      },
      {
        "command": "/vibe-test",
        "description": "Send test standup to yourself",
        "usage_hint": ""
      },
      {
        "command": "/vibe-help",
        "description": "Show help",
        "usage_hint": ""
      }
    ]
  },
  "oauth_config": {
    "redirect_urls": [
      "https://your-app.railway.app/slack/oauth_redirect"
    ],
    "scopes": {
      "bot": [
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
      ]
    }
  },
  "settings": {
    "event_subscriptions": {
      "request_url": "https://your-app.railway.app/slack/events",
      "bot_events": [
        "app_home_opened",
        "team_join"
      ]
    },
    "interactivity": {
      "is_enabled": true,
      "request_url": "https://your-app.railway.app/slack/events"
    },
    "org_deploy_enabled": false,
    "socket_mode_enabled": false,
    "token_rotation_enabled": true
  }
}
```

**Important**: Replace all instances of `your-app.railway.app` with your actual deployment URL!

---

## Troubleshooting

### "URL verification failed"

- Check that your app is deployed and running
- Verify the URL is correct and accessible
- Check logs for incoming requests
- Ensure `/slack/events` endpoint is working

### "Invalid signing secret"

- Verify `SLACK_SIGNING_SECRET` in environment variables
- Check for typos or extra spaces
- Redeploy after updating

### Commands not appearing

- Wait a few minutes after creation
- Try in a different channel
- Check app is installed to workspace
- Verify commands are saved in Slack dashboard

### OAuth errors

- Verify redirect URL matches exactly
- Check `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET`
- Ensure app is approved for distribution

### Permissions errors

- Verify all required scopes are added
- Reinstall app to grant new permissions
- Check bot is invited to channels

---

## Security Best Practices

1. **Keep credentials secret**: Never commit to git
2. **Rotate tokens**: If compromised, regenerate in Slack dashboard
3. **Limit admin access**: Only trusted users should have admin commands
4. **Monitor logs**: Watch for suspicious activity
5. **Regular updates**: Keep dependencies up to date

---

## Multi-Workspace Distribution

To distribute to multiple workspaces:

1. **Manage Distribution** → **Activate Public Distribution**

2. Complete the review checklist

3. Share installation URL: `https://your-app.railway.app/`

4. Each workspace gets isolated data automatically

---

## Admin Management

The user who installs the app becomes the first admin. To add more admins:

1. Update database directly (future: add `/vibe-add-admin` command):
   ```sql
   UPDATE workspaces
   SET admin_user_ids = array_append(admin_user_ids, 'U123ABC456')
   WHERE team_id = 'T123ABC';
   ```

2. Or modify in code and redeploy

---

## Next Steps

1. ✅ App created and configured
2. ✅ Installed to workspace
3. ✅ Tested commands
4. ✅ Created vibe check channel
5. ➡️ Add your first clients
6. ➡️ Monitor first standups
7. ➡️ Review Friday feedback

Your Slack app is ready! 🎉

For deployment details, see [DEPLOYMENT.md](DEPLOYMENT.md)

For usage instructions, see [README.md](../README.md)
