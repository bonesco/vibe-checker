# 🎭 Vibe Check - Client Communication Slack App

Professional Slack app for managing client relationships through automated daily standups and weekly feedback collection.

## Features

- **📋 Daily Standups**: Automated DM standup requests (daily or Monday-only)
- **🎭 Weekly Feedback**: Friday feedback collection with satisfaction ratings
- **🔒 Private & Secure**: All responses are private until posted to your vibe check channel
- **⚡ Multi-Workspace**: Support for multiple client workspaces with isolated data
- **🎯 Easy Management**: Slash commands for all admin tasks
- **📊 Analytics Ready**: Track response rates and satisfaction trends

## Architecture

- **Backend**: Python 3.11 with Slack Bolt framework
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Scheduling**: APScheduler with database-backed job store
- **Hosting**: Railway (or any Python-compatible platform)
- **Security**: Fernet encryption for tokens, signature verification

## Project Structure

```
vibe-check-slack/
├── app.py                      # Main entry point
├── requirements.txt            # Python dependencies
├── Procfile                    # Railway deployment config
├── runtime.txt                 # Python version
├── .env.example                # Environment template
├── alembic.ini                 # Database migrations config
│
├── src/
│   ├── config.py               # Configuration management
│   ├── app_factory.py          # Slack Bolt app setup
│   │
│   ├── models/                 # Database models
│   │   ├── workspace.py
│   │   ├── client.py
│   │   ├── standup_config.py
│   │   ├── feedback_config.py
│   │   ├── standup_response.py
│   │   └── feedback_response.py
│   │
│   ├── services/               # Business logic
│   │   ├── workspace_service.py
│   │   ├── client_service.py
│   │   ├── standup_service.py
│   │   ├── feedback_service.py
│   │   └── scheduler_service.py
│   │
│   ├── handlers/               # Slack event handlers
│   │   ├── commands.py
│   │   ├── actions.py
│   │   ├── views.py
│   │   └── events.py
│   │
│   ├── blocks/                 # Block Kit UI templates
│   │   ├── standup_blocks.py
│   │   ├── feedback_blocks.py
│   │   └── admin_blocks.py
│   │
│   ├── utils/                  # Utilities
│   │   ├── encryption.py
│   │   ├── logger.py
│   │   └── validators.py
│   │
│   └── middleware/             # Middleware
│       ├── auth_middleware.py
│       └── error_middleware.py
│
├── scripts/
│   ├── init_db.py              # Initialize database
│   └── migrate.py              # Run migrations
│
└── docs/
    ├── DEPLOYMENT.md           # Deployment guide
    ├── SLACK_SETUP.md          # Slack app setup
    └── slack_manifest.json     # Slack app manifest
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database
- Slack workspace with admin access
- Railway account (or alternative hosting)

### Local Development Setup

1. **Clone and setup environment**:
   ```bash
   cd "Vibe Check"
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your values (see below)
   ```

3. **Generate encryption key**:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   # Add output to .env as ENCRYPTION_KEY
   ```

4. **Set up local PostgreSQL**:
   ```bash
   createdb vibe_check
   # Update DATABASE_URL in .env
   ```

5. **Initialize database**:
   ```bash
   python scripts/init_db.py
   ```

6. **Run the app**:
   ```bash
   python app.py
   ```

### Environment Variables

Required variables in `.env`:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/vibe_check

# Slack App Credentials (from https://api.slack.com/apps)
SLACK_CLIENT_ID=your_client_id
SLACK_CLIENT_SECRET=your_client_secret
SLACK_SIGNING_SECRET=your_signing_secret

# Security (generate with command above)
ENCRYPTION_KEY=your_fernet_key_here

# Application
PORT=8000
LOG_LEVEL=INFO
RAILWAY_STATIC_URL=https://your-app.railway.app

# Features
ENABLE_REMINDERS=true
REMINDER_DELAY_HOURS=4
DATA_RETENTION_DAYS=90
```

## Slack App Setup

See [docs/SLACK_SETUP.md](docs/SLACK_SETUP.md) for detailed instructions on:
- Creating your Slack app
- Configuring OAuth scopes
- Setting up slash commands
- Enabling interactivity
- Installing to your workspace

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for deployment guides for:
- Railway (recommended)
- Heroku
- AWS
- Docker

## Usage

### Admin Commands

Once installed, use these slash commands in Slack:

- `/vibe-add-client` - Add a new client to receive standups
- `/vibe-list-clients` - View all active clients and their configs
- `/vibe-pause` - Temporarily pause standups for a client
- `/vibe-resume` - Resume paused standups
- `/vibe-test` - Send a test standup to yourself
- `/vibe-help` - Show help documentation

### Workflow

1. **Install app** to your Slack workspace
2. **Add clients** using `/vibe-add-client`
3. **Configure schedules** (daily or Monday-only standups)
4. **Set vibe channel** where feedback will be posted
5. **Clients receive** automated DMs at scheduled times
6. **View feedback** in your private vibe check channel

## Development

### Running Tests

```bash
pytest
pytest --cov=src  # With coverage
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Code Style

```bash
# Format code
black src/

# Lint
flake8 src/
```

## TODO / Future Enhancements

- [ ] Complete state extraction in action handlers (currently simplified)
- [ ] Add analytics dashboard command `/vibe-analytics`
- [ ] Implement reminder jobs for non-responses
- [ ] Add `/vibe-config-standup` and `/vibe-config-feedback` commands
- [ ] Create App Home tab with stats
- [ ] Add data export functionality
- [ ] Implement GDPR compliance endpoints
- [ ] Add unit and integration tests
- [ ] Set up CI/CD pipeline
- [ ] Add monitoring and alerting

## Troubleshooting

### Common Issues

**Database connection errors**:
- Verify DATABASE_URL is correct
- Ensure PostgreSQL is running
- Check network/firewall settings

**Slack API errors**:
- Verify all environment variables are set
- Check Slack app configuration matches docs
- Ensure bot has required scopes

**Jobs not running**:
- Check scheduler is initialized (logs should show "APScheduler started")
- Verify jobs are added (check `apscheduler_jobs` table)
- Check timezone settings

### Logs

View application logs:
```bash
# Local
python app.py  # Logs to stdout

# Railway
railway logs  # Live logs
```

## Security

- Tokens encrypted at rest using Fernet symmetric encryption
- Request signature verification enabled
- Admin-only command access
- Secure OAuth flow
- No sensitive data in logs

## Contributing

This is a custom internal tool. For issues or enhancements:
1. Document the issue/feature
2. Make changes in a branch
3. Test thoroughly
4. Deploy to staging first

## License

Proprietary - Internal use only

## Support

For questions or issues:
- Check logs first
- Review [DEPLOYMENT.md](docs/DEPLOYMENT.md)
- Check [SLACK_SETUP.md](docs/SLACK_SETUP.md)
- Contact the development team

---

Built with ❤️ using Slack Bolt for Python
