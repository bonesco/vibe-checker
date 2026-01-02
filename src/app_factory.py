"""Slack Bolt app factory"""

import os
import secrets
from functools import wraps
from datetime import datetime
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, jsonify, render_template_string
from src.config import config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def require_admin_auth(f):
    """Decorator to require API key authentication for admin endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if admin API key is configured
        if not config.ADMIN_API_KEY:
            logger.warning("Admin endpoint accessed but ADMIN_API_KEY not configured")
            return """
            <html>
                <head><title>Admin Not Configured</title></head>
                <body style="font-family: sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
                    <h1>Admin Access Not Configured</h1>
                    <p>To enable the admin dashboard, set the <code>ADMIN_API_KEY</code> environment variable.</p>
                    <p>Generate a secure key with:</p>
                    <pre style="background: #f5f5f5; padding: 10px;">python -c "import secrets; print(secrets.token_urlsafe(32))"</pre>
                    <p>Then access the dashboard with <code>/admin?key=YOUR_KEY</code></p>
                </body>
            </html>
            """, 503

        # Check for API key in header or query param
        provided_key = request.headers.get('X-Admin-Key') or request.args.get('key')

        if not provided_key:
            return """
            <html>
                <head><title>Authentication Required</title></head>
                <body style="font-family: sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
                    <h1>Authentication Required</h1>
                    <p>Access the admin dashboard with your API key:</p>
                    <ul>
                        <li>Add <code>?key=YOUR_API_KEY</code> to the URL, or</li>
                        <li>Set the <code>X-Admin-Key</code> header</li>
                    </ul>
                </body>
            </html>
            """, 401

        # Constant-time comparison to prevent timing attacks
        if not secrets.compare_digest(provided_key, config.ADMIN_API_KEY):
            logger.warning(f"Invalid admin API key attempt from {request.remote_addr}")
            return jsonify({"error": "Invalid API key"}), 403

        return f(*args, **kwargs)
    return decorated_function


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


DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Vibe Check - Admin Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 20px;
            margin-bottom: 30px;
        }
        header h1 { font-size: 2em; margin-bottom: 5px; }
        header p { opacity: 0.9; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-card h3 { font-size: 2.5em; color: #667eea; }
        .stat-card p { color: #666; font-size: 0.9em; }
        .card {
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            overflow: hidden;
        }
        .card-header {
            background: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .card-header h2 { font-size: 1.2em; }
        .card-body { padding: 20px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; }
        tr:hover { background: #f8f9fa; }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 500;
        }
        .badge-success { background: #d4edda; color: #155724; }
        .badge-warning { background: #fff3cd; color: #856404; }
        .badge-info { background: #d1ecf1; color: #0c5460; }
        .badge-danger { background: #f8d7da; color: #721c24; }
        .btn {
            display: inline-block;
            padding: 8px 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9em;
            text-decoration: none;
            transition: opacity 0.2s;
        }
        .btn:hover { opacity: 0.8; }
        .btn-primary { background: #667eea; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-sm { padding: 5px 10px; font-size: 0.8em; }
        .actions { display: flex; gap: 5px; }
        .empty-state { text-align: center; padding: 40px; color: #666; }
        .refresh-note { text-align: center; color: #666; font-size: 0.85em; margin-top: 20px; }
        .status-dot {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 5px;
        }
        .status-active { background: #28a745; }
        .status-paused { background: #ffc107; }
        .status-inactive { background: #dc3545; }
        @media (max-width: 768px) {
            .stats { grid-template-columns: 1fr 1fr; }
            table { font-size: 0.85em; }
            th, td { padding: 8px; }
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>🎭 Vibe Check Dashboard</h1>
            <p>Manage your client check-ins and view responses</p>
        </div>
    </header>

    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <h3>{{ stats.total_clients }}</h3>
                <p>Total Clients</p>
            </div>
            <div class="stat-card">
                <h3>{{ stats.active_clients }}</h3>
                <p>Active Clients</p>
            </div>
            <div class="stat-card">
                <h3>{{ stats.scheduled_jobs }}</h3>
                <p>Scheduled Jobs</p>
            </div>
            <div class="stat-card">
                <h3>{{ stats.responses_today }}</h3>
                <p>Responses Today</p>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <h2>📋 Clients</h2>
                <a href="/admin/refresh?key={{ request.args.get('key', '') }}" class="btn btn-primary btn-sm">↻ Refresh</a>
            </div>
            <div class="card-body">
                {% if clients %}
                <table>
                    <thead>
                        <tr>
                            <th>Client</th>
                            <th>Schedule</th>
                            <th>Next Send</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for client in clients %}
                        <tr>
                            <td>
                                <strong>{{ client.display_name }}</strong>
                                <br><small style="color:#666">{{ client.timezone }}</small>
                            </td>
                            <td>
                                {% if client.schedule %}
                                    {{ client.schedule }}
                                {% else %}
                                    <span style="color:#999">Not configured</span>
                                {% endif %}
                            </td>
                            <td>
                                {% if client.next_run %}
                                    {{ client.next_run }}
                                {% else %}
                                    <span style="color:#999">-</span>
                                {% endif %}
                            </td>
                            <td>
                                {% if client.is_paused %}
                                    <span class="badge badge-warning">⏸ Paused</span>
                                {% elif client.is_active %}
                                    <span class="badge badge-success">✓ Active</span>
                                {% else %}
                                    <span class="badge badge-danger">Inactive</span>
                                {% endif %}
                            </td>
                            <td class="actions">
                                <a href="/admin/send/standup/{{ client.id }}?key={{ request.args.get('key', '') }}" class="btn btn-success btn-sm" onclick="return confirm('Send standup to {{ client.display_name }} now?')">Send Now</a>
                                <a href="/admin/send/feedback/{{ client.id }}?key={{ request.args.get('key', '') }}" class="btn btn-info btn-sm" style="background:#17a2b8" onclick="return confirm('Send feedback form to {{ client.display_name }} now?')">Feedback</a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <div class="empty-state">
                    <p>No clients yet. Use <code>/vibe-add-client</code> in Slack to add clients.</p>
                </div>
                {% endif %}
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <h2>⏰ Scheduled Jobs</h2>
            </div>
            <div class="card-body">
                {% if jobs %}
                <table>
                    <thead>
                        <tr>
                            <th>Job ID</th>
                            <th>Type</th>
                            <th>Next Run</th>
                            <th>Trigger</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for job in jobs %}
                        <tr>
                            <td><code>{{ job.id }}</code></td>
                            <td>
                                {% if 'standup' in job.id %}
                                    <span class="badge badge-info">Standup</span>
                                {% else %}
                                    <span class="badge badge-success">Feedback</span>
                                {% endif %}
                            </td>
                            <td>{{ job.next_run or 'Not scheduled' }}</td>
                            <td><small>{{ job.trigger }}</small></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <div class="empty-state">
                    <p>No scheduled jobs. Jobs are created when you add clients.</p>
                </div>
                {% endif %}
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <h2>📊 Recent Responses</h2>
            </div>
            <div class="card-body">
                {% if responses %}
                <table>
                    <thead>
                        <tr>
                            <th>Client</th>
                            <th>Type</th>
                            <th>Date</th>
                            <th>Response Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for response in responses %}
                        <tr>
                            <td>{{ response.client_name }}</td>
                            <td>
                                <span class="badge badge-{{ 'info' if response.type == 'standup' else 'success' }}">
                                    {{ response.type | capitalize }}
                                </span>
                            </td>
                            <td>{{ response.date }}</td>
                            <td>{{ response.response_time }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <div class="empty-state">
                    <p>No responses yet. Responses will appear here once clients submit their standups or feedback.</p>
                </div>
                {% endif %}
            </div>
        </div>

        <p class="refresh-note">Dashboard data refreshes on page load. <a href="/admin?key={{ request.args.get('key', '') }}">Refresh now</a></p>
    </div>
</body>
</html>
"""


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
        logger.info(f"Received Slack request: {request.content_type}")
        try:
            result = handler.handle(request)
            logger.info(f"Slack request handled successfully")
            return result
        except Exception as e:
            logger.error(f"Error handling Slack request: {e}", exc_info=True)
            raise

    @flask_app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint for Railway"""
        return jsonify({"status": "ok"}), 200

    @flask_app.route("/", methods=["GET"])
    def home():
        """Home page"""
        return """
        <html>
            <head>
                <title>Vibe Check - Slack App</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        max-width: 600px;
                        margin: 100px auto;
                        padding: 20px;
                        text-align: center;
                    }
                    h1 { color: #333; }
                    p { color: #666; margin-bottom: 20px; }
                    a { color: #667eea; }
                    code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; }
                </style>
            </head>
            <body>
                <h1>🎭 Vibe Check</h1>
                <p>Slack app is running. Use <code>/vibe-help</code> in Slack to get started.</p>
                <p style="font-size: 0.9em; color: #999;">Admin dashboard available at <code>/admin?key=YOUR_API_KEY</code></p>
            </body>
        </html>
        """

    @flask_app.route("/admin", methods=["GET"])
    @flask_app.route("/admin/", methods=["GET"])
    @require_admin_auth
    def admin_dashboard():
        """Admin dashboard"""
        from sqlalchemy.orm import joinedload
        from src.database.session import get_session
        from src.models.client import Client
        from src.models.standup_response import StandupResponse
        from src.models.feedback_response import FeedbackResponse
        from src.services.scheduler_service import get_scheduled_jobs
        from datetime import date, timedelta

        session = get_session()
        try:
            # Get all clients with their configs (eager load relationships)
            clients = session.query(Client).options(
                joinedload(Client.standup_config),
                joinedload(Client.feedback_config)
            ).filter_by(is_active=True).all()

            # Get scheduled jobs
            jobs = get_scheduled_jobs()

            # Create a map of job next_run times by client_id
            job_next_runs = {}
            for job in jobs:
                # Parse client_id from job id (format: standup_workspace_clientid or feedback_workspace_clientid)
                parts = job['id'].split('_')
                if len(parts) >= 3:
                    try:
                        client_id = int(parts[2])
                        if job['next_run']:
                            job_next_runs[client_id] = job['next_run'].strftime('%Y-%m-%d %H:%M') if hasattr(job['next_run'], 'strftime') else str(job['next_run'])
                    except (ValueError, IndexError):
                        pass

            # Build client data list to avoid template issues with ORM objects
            client_data = []
            for client in clients:
                schedule_str = None
                if client.standup_config and client.standup_config.schedule_time:
                    schedule_type = 'Daily' if client.standup_config.schedule_type == 'daily' else 'Mondays'
                    schedule_time = client.standup_config.schedule_time.strftime('%I:%M %p')
                    schedule_str = f"{schedule_type} at {schedule_time}"

                client_data.append({
                    'id': client.id,
                    'display_name': client.display_name or client.slack_user_id,
                    'timezone': client.timezone,
                    'schedule': schedule_str,
                    'next_run': job_next_runs.get(client.id),
                    'is_active': client.is_active,
                    'is_paused': client.standup_config.is_paused if client.standup_config else False
                })

            # Get today's responses
            today = date.today()
            standup_responses_today = session.query(StandupResponse).filter(
                StandupResponse.scheduled_date == today
            ).count()

            feedback_responses_today = session.query(FeedbackResponse).filter(
                FeedbackResponse.week_ending >= today - timedelta(days=7)
            ).count()

            # Get recent responses
            recent_standups = session.query(StandupResponse).order_by(
                StandupResponse.submitted_at.desc()
            ).limit(5).all()

            recent_feedbacks = session.query(FeedbackResponse).order_by(
                FeedbackResponse.submitted_at.desc()
            ).limit(5).all()

            responses = []
            for r in recent_standups:
                client = session.query(Client).filter_by(id=r.client_id).first()
                responses.append({
                    'client_name': client.display_name if client else f"Client {r.client_id}",
                    'type': 'standup',
                    'date': r.scheduled_date.strftime('%Y-%m-%d') if r.scheduled_date else '-',
                    'response_time': f"{r.response_time_seconds // 60}m" if r.response_time_seconds else '-'
                })

            for r in recent_feedbacks:
                client = session.query(Client).filter_by(id=r.client_id).first()
                responses.append({
                    'client_name': client.display_name if client else f"Client {r.client_id}",
                    'type': 'feedback',
                    'date': r.week_ending.strftime('%Y-%m-%d') if r.week_ending else '-',
                    'response_time': f"{r.response_time_seconds // 60}m" if r.response_time_seconds else '-'
                })

            # Sort responses by date
            responses.sort(key=lambda x: x['date'], reverse=True)
            responses = responses[:10]

            stats = {
                'total_clients': len(client_data),
                'active_clients': len([c for c in client_data if not c['is_paused']]),
                'scheduled_jobs': len(jobs),
                'responses_today': standup_responses_today + feedback_responses_today
            }

            return render_template_string(
                DASHBOARD_HTML,
                clients=client_data,
                jobs=jobs,
                responses=responses,
                stats=stats
            )
        except Exception as e:
            logger.error(f"Admin dashboard error: {e}", exc_info=True)
            return f"<h1>Dashboard Error</h1><pre>{e}</pre>", 500
        finally:
            session.close()

    @flask_app.route("/admin/refresh", methods=["GET"])
    @require_admin_auth
    def admin_refresh():
        """Refresh and redirect to admin"""
        from flask import redirect
        # Preserve the API key in the redirect
        key = request.args.get('key', '')
        return redirect(f'/admin?key={key}' if key else '/admin')

    @flask_app.route("/admin/send/standup/<int:client_id>", methods=["GET"])
    @require_admin_auth
    def send_standup_now(client_id):
        """Manually send standup to a client"""
        from flask import redirect
        from src.database.session import get_session
        from src.models.client import Client
        from src.services.standup_service import send_standup_dm

        session = get_session()
        try:
            client = session.query(Client).filter_by(id=client_id).first()
            if client:
                send_standup_dm(client.workspace_id, client_id)
                logger.info(f"Manual standup sent to client {client_id}")
        except Exception as e:
            logger.error(f"Error sending manual standup: {e}")
        finally:
            session.close()

        # Preserve the API key in the redirect
        key = request.args.get('key', '')
        return redirect(f'/admin?key={key}' if key else '/admin')

    @flask_app.route("/admin/send/feedback/<int:client_id>", methods=["GET"])
    @require_admin_auth
    def send_feedback_now(client_id):
        """Manually send feedback to a client"""
        from flask import redirect
        from src.database.session import get_session
        from src.models.client import Client
        from src.services.feedback_service import send_feedback_dm

        session = get_session()
        try:
            client = session.query(Client).filter_by(id=client_id).first()
            if client:
                send_feedback_dm(client.workspace_id, client_id)
                logger.info(f"Manual feedback sent to client {client_id}")
        except Exception as e:
            logger.error(f"Error sending manual feedback: {e}")
        finally:
            session.close()

        # Preserve the API key in the redirect
        key = request.args.get('key', '')
        return redirect(f'/admin?key={key}' if key else '/admin')

    @flask_app.route("/api/clients", methods=["GET"])
    @require_admin_auth
    def api_clients():
        """API endpoint to get all clients"""
        from src.database.session import get_session
        from src.models.client import Client

        session = get_session()
        try:
            clients = session.query(Client).filter_by(is_active=True).all()
            return jsonify([{
                'id': c.id,
                'slack_user_id': c.slack_user_id,
                'display_name': c.display_name,
                'timezone': c.timezone,
                'is_active': c.is_active,
                'schedule_type': c.standup_config.schedule_type if c.standup_config else None,
                'schedule_time': c.standup_config.schedule_time.strftime('%H:%M') if c.standup_config else None,
                'is_paused': c.standup_config.is_paused if c.standup_config else None
            } for c in clients])
        finally:
            session.close()

    @flask_app.route("/api/jobs", methods=["GET"])
    @require_admin_auth
    def api_jobs():
        """API endpoint to get scheduled jobs"""
        from src.services.scheduler_service import get_scheduled_jobs
        jobs = get_scheduled_jobs()
        return jsonify([{
            'id': j['id'],
            'name': j['name'],
            'next_run': str(j['next_run']) if j['next_run'] else None,
            'trigger': j['trigger']
        } for j in jobs])

    logger.info("Flask app configured")
    return flask_app
