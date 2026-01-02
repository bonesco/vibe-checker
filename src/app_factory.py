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
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 20px;
            margin-bottom: 30px;
        }
        .header-content { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
        header h1 { font-size: 2em; margin-bottom: 5px; }
        header p { opacity: 0.9; }
        .header-actions { display: flex; gap: 10px; align-items: center; }
        .auto-refresh { display: flex; align-items: center; gap: 5px; font-size: 0.9em; }
        .auto-refresh input { cursor: pointer; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-card.highlight { border-left: 4px solid #667eea; }
        .stat-card h3 { font-size: 2.2em; color: #667eea; margin-bottom: 5px; }
        .stat-card p { color: #666; font-size: 0.85em; }
        .stat-card .trend { font-size: 0.75em; margin-top: 5px; }
        .stat-card .trend.up { color: #28a745; }
        .stat-card .trend.down { color: #dc3545; }
        .stat-card .emoji { font-size: 1.5em; margin-bottom: 10px; }
        .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
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
        .card-header h2 { font-size: 1.1em; display: flex; align-items: center; gap: 8px; }
        .card-body { padding: 20px; }
        .card-body.compact { padding: 0; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; font-size: 0.85em; text-transform: uppercase; color: #666; }
        tr:hover { background: #f8f9fa; }
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.75em;
            font-weight: 500;
        }
        .badge-success { background: #d4edda; color: #155724; }
        .badge-warning { background: #fff3cd; color: #856404; }
        .badge-info { background: #d1ecf1; color: #0c5460; }
        .badge-danger { background: #f8d7da; color: #721c24; }
        .badge-secondary { background: #e9ecef; color: #495057; }
        .badge-purple { background: #e8daef; color: #6c3483; }
        .btn {
            display: inline-block;
            padding: 6px 12px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.8em;
            text-decoration: none;
            transition: all 0.2s;
        }
        .btn:hover { opacity: 0.85; transform: translateY(-1px); }
        .btn-primary { background: #667eea; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-warning { background: #ffc107; color: #333; }
        .btn-info { background: #17a2b8; color: white; }
        .btn-outline { background: transparent; border: 1px solid #ddd; color: #666; }
        .btn-outline:hover { background: #f8f9fa; }
        .btn-sm { padding: 4px 8px; font-size: 0.75em; }
        .actions { display: flex; gap: 5px; flex-wrap: wrap; }
        .empty-state { text-align: center; padding: 40px; color: #666; }
        .refresh-note { text-align: center; color: #666; font-size: 0.85em; margin-top: 20px; }
        .client-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 0.9em;
            margin-right: 10px;
        }
        .client-info { display: flex; align-items: center; }
        .client-details { display: flex; flex-direction: column; }
        .client-name { font-weight: 600; }
        .client-meta { font-size: 0.8em; color: #666; }
        .schedule-info { display: flex; flex-direction: column; gap: 4px; }
        .schedule-item { display: flex; align-items: center; gap: 5px; font-size: 0.85em; }
        .schedule-item .icon { width: 16px; text-align: center; }
        .response-preview {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 12px;
            margin: 10px 0;
            font-size: 0.9em;
        }
        .response-preview .label { font-weight: 600; color: #666; font-size: 0.8em; margin-bottom: 4px; }
        .response-preview .content { color: #333; }
        .rating-display { display: flex; align-items: center; gap: 3px; }
        .tab-container { display: flex; gap: 5px; }
        .tab {
            padding: 8px 16px;
            border: none;
            background: transparent;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            font-size: 0.9em;
            color: #666;
        }
        .tab:hover { color: #333; }
        .tab.active { color: #667eea; border-bottom-color: #667eea; font-weight: 500; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .tooltip {
            position: relative;
            cursor: help;
        }
        .tooltip:hover::after {
            content: attr(data-tooltip);
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: #333;
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 0.75em;
            white-space: nowrap;
            z-index: 100;
        }
        @media (max-width: 768px) {
            .stats { grid-template-columns: 1fr 1fr; }
            .grid-2 { grid-template-columns: 1fr; }
            table { font-size: 0.85em; }
            th, td { padding: 8px; }
            .header-content { flex-direction: column; align-items: flex-start; }
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <div class="header-content">
                <div>
                    <h1>🎭 Vibe Check Dashboard</h1>
                    <p>Manage your client check-ins and view responses</p>
                </div>
                <div class="header-actions">
                    <label class="auto-refresh">
                        <input type="checkbox" id="autoRefresh" onchange="toggleAutoRefresh()">
                        Auto-refresh (30s)
                    </label>
                    <a href="/admin/refresh?key={{ request.args.get('key', '') }}" class="btn btn-outline" style="color:white;border-color:rgba(255,255,255,0.5)">↻ Refresh</a>
                </div>
            </div>
        </div>
    </header>

    <div class="container">
        <div class="stats">
            <div class="stat-card highlight">
                <div class="emoji">👥</div>
                <h3>{{ stats.total_clients }}</h3>
                <p>Total Clients</p>
            </div>
            <div class="stat-card">
                <div class="emoji">✅</div>
                <h3>{{ stats.active_clients }}</h3>
                <p>Active (Not Paused)</p>
            </div>
            <div class="stat-card">
                <div class="emoji">📅</div>
                <h3>{{ stats.scheduled_jobs }}</h3>
                <p>Scheduled Jobs</p>
            </div>
            <div class="stat-card">
                <div class="emoji">📝</div>
                <h3>{{ stats.responses_today }}</h3>
                <p>Responses Today</p>
            </div>
            <div class="stat-card">
                <div class="emoji">{{ '😄' if stats.avg_feeling >= 4 else '🙂' if stats.avg_feeling >= 3 else '😐' if stats.avg_feeling >= 2 else '📊' }}</div>
                <h3>{{ '%.1f' | format(stats.avg_feeling) if stats.avg_feeling else '-' }}</h3>
                <p>Avg Feeling (7d)</p>
            </div>
            <div class="stat-card">
                <div class="emoji">⭐</div>
                <h3>{{ '%.1f' | format(stats.avg_satisfaction) if stats.avg_satisfaction else '-' }}</h3>
                <p>Avg Satisfaction (7d)</p>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <h2>📋 Clients</h2>
                <div class="tab-container">
                    <button class="tab active" onclick="showTab('all')">All ({{ clients|length }})</button>
                    <button class="tab" onclick="showTab('active')">Active</button>
                    <button class="tab" onclick="showTab('paused')">Paused</button>
                </div>
            </div>
            <div class="card-body compact">
                {% if clients %}
                <table>
                    <thead>
                        <tr>
                            <th>Client</th>
                            <th>Check-ins</th>
                            <th>Next Send</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="clientsTable">
                        {% for client in clients %}
                        <tr data-status="{{ 'paused' if client.is_paused else 'active' }}">
                            <td>
                                <div class="client-info">
                                    <div class="client-avatar">{{ client.display_name[0] | upper }}</div>
                                    <div class="client-details">
                                        <span class="client-name">{{ client.display_name }}</span>
                                        <span class="client-meta">{{ client.timezone }}</span>
                                    </div>
                                </div>
                            </td>
                            <td>
                                <div class="schedule-info">
                                    {% if client.standup_schedule %}
                                    <div class="schedule-item">
                                        <span class="icon">📋</span>
                                        <span>{{ client.standup_schedule }}</span>
                                    </div>
                                    {% endif %}
                                    {% if client.vibe_check_enabled %}
                                    <div class="schedule-item">
                                        <span class="icon">🎭</span>
                                        <span>Fridays at {{ client.vibe_check_time }}</span>
                                    </div>
                                    {% endif %}
                                    {% if not client.standup_schedule and not client.vibe_check_enabled %}
                                    <span style="color:#999">None configured</span>
                                    {% endif %}
                                </div>
                            </td>
                            <td>
                                {% if client.next_run %}
                                    <span class="tooltip" data-tooltip="Next scheduled send">{{ client.next_run }}</span>
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
                                {% if client.standup_schedule %}
                                <a href="/admin/send/standup/{{ client.id }}?key={{ request.args.get('key', '') }}" class="btn btn-success btn-sm" onclick="return confirm('Send standup to {{ client.display_name }} now?')" title="Send Standup">📋</a>
                                {% endif %}
                                {% if client.vibe_check_enabled %}
                                <a href="/admin/send/feedback/{{ client.id }}?key={{ request.args.get('key', '') }}" class="btn btn-info btn-sm" onclick="return confirm('Send vibe check to {{ client.display_name }} now?')" title="Send Vibe Check">🎭</a>
                                {% endif %}
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

        <div class="grid-2">
            <div class="card">
                <div class="card-header">
                    <h2>📊 Recent Responses</h2>
                </div>
                <div class="card-body compact">
                    {% if responses %}
                    <table>
                        <thead>
                            <tr>
                                <th>Client</th>
                                <th>Type</th>
                                <th>Rating</th>
                                <th>Date</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for response in responses %}
                            <tr>
                                <td>{{ response.client_name }}</td>
                                <td>
                                    <span class="badge badge-{{ 'info' if response.type == 'standup' else 'purple' }}">
                                        {{ 'Standup' if response.type == 'standup' else 'Vibe Check' }}
                                    </span>
                                </td>
                                <td>
                                    {% if response.rating %}
                                    <span class="rating-display">
                                        {{ response.rating_emoji }} {{ response.rating }}/5
                                    </span>
                                    {% else %}
                                    <span style="color:#999">-</span>
                                    {% endif %}
                                </td>
                                <td>
                                    <span class="tooltip" data-tooltip="{{ response.response_time }}">{{ response.date }}</span>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                    {% else %}
                    <div class="empty-state">
                        <p>No responses yet.</p>
                    </div>
                    {% endif %}
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <h2>⏰ Scheduled Jobs</h2>
                </div>
                <div class="card-body compact">
                    {% if jobs %}
                    <table>
                        <thead>
                            <tr>
                                <th>Type</th>
                                <th>Next Run</th>
                                <th>Schedule</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for job in jobs %}
                            <tr>
                                <td>
                                    {% if 'standup' in job.id %}
                                        <span class="badge badge-info">📋 Standup</span>
                                    {% else %}
                                        <span class="badge badge-purple">🎭 Vibe Check</span>
                                    {% endif %}
                                </td>
                                <td>{{ job.next_run_formatted or 'Not scheduled' }}</td>
                                <td><small style="color:#666">{{ job.trigger }}</small></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                    {% else %}
                    <div class="empty-state">
                        <p>No scheduled jobs.</p>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>

        {% if latest_responses %}
        <div class="card">
            <div class="card-header">
                <h2>💬 Latest Response Details</h2>
            </div>
            <div class="card-body">
                {% for resp in latest_responses[:3] %}
                <div class="response-preview">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                        <strong>{{ resp.client_name }}</strong>
                        <span class="badge badge-{{ 'info' if resp.type == 'standup' else 'purple' }}">
                            {{ 'Standup' if resp.type == 'standup' else 'Vibe Check' }} - {{ resp.date }}
                        </span>
                    </div>
                    {% if resp.type == 'standup' %}
                        {% if resp.accomplishments %}
                        <div class="label">✅ Accomplishments</div>
                        <div class="content">{{ resp.accomplishments }}</div>
                        {% endif %}
                        {% if resp.working_on %}
                        <div class="label" style="margin-top:8px">🎯 Today's Focus</div>
                        <div class="content">{{ resp.working_on }}</div>
                        {% endif %}
                    {% else %}
                        {% if resp.feeling_text %}
                        <div class="label">🏆 What went well</div>
                        <div class="content">{{ resp.feeling_text }}</div>
                        {% endif %}
                        {% if resp.improvements %}
                        <div class="label" style="margin-top:8px">💡 Improvements</div>
                        <div class="content">{{ resp.improvements }}</div>
                        {% endif %}
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <p class="refresh-note">
            Last updated: <span id="lastUpdate">{{ now }}</span>
            <span id="countdown"></span>
        </p>
    </div>

    <script>
        let refreshInterval;

        function toggleAutoRefresh() {
            const checkbox = document.getElementById('autoRefresh');
            if (checkbox.checked) {
                refreshInterval = setInterval(() => {
                    window.location.reload();
                }, 30000);
                updateCountdown(30);
            } else {
                clearInterval(refreshInterval);
                document.getElementById('countdown').textContent = '';
            }
        }

        function updateCountdown(seconds) {
            const el = document.getElementById('countdown');
            let remaining = seconds;
            const countdownInterval = setInterval(() => {
                remaining--;
                if (remaining <= 0) {
                    clearInterval(countdownInterval);
                } else {
                    el.textContent = ` (refreshing in ${remaining}s)`;
                }
            }, 1000);
        }

        function showTab(filter) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');

            document.querySelectorAll('#clientsTable tr').forEach(row => {
                if (filter === 'all') {
                    row.style.display = '';
                } else {
                    row.style.display = row.dataset.status === filter ? '' : 'none';
                }
            });
        }
    </script>
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
        from sqlalchemy import func
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
                parts = job['id'].split('_')
                if len(parts) >= 3:
                    try:
                        client_id = int(parts[2])
                        if job['next_run']:
                            job_next_runs[client_id] = job['next_run'].strftime('%b %d %H:%M') if hasattr(job['next_run'], 'strftime') else str(job['next_run'])
                    except (ValueError, IndexError):
                        pass

            # Build client data with both standup and vibe check info
            client_data = []
            for client in clients:
                standup_schedule = None
                if client.standup_config and client.standup_config.schedule_time:
                    schedule_type = 'Daily' if client.standup_config.schedule_type == 'daily' else 'Mon'
                    schedule_time = client.standup_config.schedule_time.strftime('%I:%M %p')
                    standup_schedule = f"{schedule_type} at {schedule_time}"

                vibe_check_enabled = client.feedback_config and client.feedback_config.is_enabled
                vibe_check_time = client.feedback_config.schedule_time.strftime('%I:%M %p') if client.feedback_config and client.feedback_config.schedule_time else '3:00 PM'

                client_data.append({
                    'id': client.id,
                    'display_name': client.display_name or client.slack_user_id,
                    'timezone': client.timezone,
                    'standup_schedule': standup_schedule,
                    'vibe_check_enabled': vibe_check_enabled,
                    'vibe_check_time': vibe_check_time,
                    'next_run': job_next_runs.get(client.id),
                    'is_active': client.is_active,
                    'is_paused': client.standup_config.is_paused if client.standup_config else False
                })

            # Get today's responses
            today = date.today()
            week_ago = today - timedelta(days=7)

            standup_responses_today = session.query(StandupResponse).filter(
                StandupResponse.scheduled_date == today
            ).count()

            feedback_responses_today = session.query(FeedbackResponse).filter(
                FeedbackResponse.week_ending >= week_ago
            ).count()

            # Calculate average ratings from last 7 days
            avg_feeling = session.query(func.avg(FeedbackResponse.feeling_rating)).filter(
                FeedbackResponse.submitted_at >= datetime.now() - timedelta(days=7),
                FeedbackResponse.feeling_rating.isnot(None)
            ).scalar()

            avg_satisfaction = session.query(func.avg(FeedbackResponse.satisfaction_rating)).filter(
                FeedbackResponse.submitted_at >= datetime.now() - timedelta(days=7),
                FeedbackResponse.satisfaction_rating.isnot(None)
            ).scalar()

            # Get recent responses with ratings
            recent_standups = session.query(StandupResponse).order_by(
                StandupResponse.submitted_at.desc()
            ).limit(5).all()

            recent_feedbacks = session.query(FeedbackResponse).order_by(
                FeedbackResponse.submitted_at.desc()
            ).limit(5).all()

            # Emoji mapping for ratings
            feeling_emojis = {5: '😄', 4: '🙂', 3: '😐', 2: '😕', 1: '😞'}

            responses = []
            latest_responses = []

            for r in recent_standups:
                client = session.query(Client).filter_by(id=r.client_id).first()
                client_name = client.display_name if client else f"Client {r.client_id}"
                responses.append({
                    'client_name': client_name,
                    'type': 'standup',
                    'date': r.scheduled_date.strftime('%b %d') if r.scheduled_date else '-',
                    'response_time': f"{r.response_time_seconds // 60}m" if r.response_time_seconds else '-',
                    'rating': None,
                    'rating_emoji': None
                })
                latest_responses.append({
                    'client_name': client_name,
                    'type': 'standup',
                    'date': r.scheduled_date.strftime('%b %d') if r.scheduled_date else '-',
                    'accomplishments': r.accomplishments[:200] + '...' if r.accomplishments and len(r.accomplishments) > 200 else r.accomplishments,
                    'working_on': r.working_on[:200] + '...' if r.working_on and len(r.working_on) > 200 else r.working_on
                })

            for r in recent_feedbacks:
                client = session.query(Client).filter_by(id=r.client_id).first()
                client_name = client.display_name if client else f"Client {r.client_id}"
                responses.append({
                    'client_name': client_name,
                    'type': 'feedback',
                    'date': r.week_ending.strftime('%b %d') if r.week_ending else '-',
                    'response_time': f"{r.response_time_seconds // 60}m" if r.response_time_seconds else '-',
                    'rating': r.feeling_rating,
                    'rating_emoji': feeling_emojis.get(r.feeling_rating, '')
                })
                latest_responses.append({
                    'client_name': client_name,
                    'type': 'feedback',
                    'date': r.week_ending.strftime('%b %d') if r.week_ending else '-',
                    'feeling_text': r.feeling_text[:200] + '...' if r.feeling_text and len(r.feeling_text) > 200 else r.feeling_text,
                    'improvements': r.improvements[:200] + '...' if r.improvements and len(r.improvements) > 200 else r.improvements
                })

            # Sort responses by date
            responses.sort(key=lambda x: x['date'], reverse=True)
            responses = responses[:10]

            # Format job next_run times
            for job in jobs:
                if job.get('next_run') and hasattr(job['next_run'], 'strftime'):
                    job['next_run_formatted'] = job['next_run'].strftime('%b %d %H:%M')
                else:
                    job['next_run_formatted'] = str(job.get('next_run', ''))

            stats = {
                'total_clients': len(client_data),
                'active_clients': len([c for c in client_data if not c['is_paused']]),
                'scheduled_jobs': len(jobs),
                'responses_today': standup_responses_today + feedback_responses_today,
                'avg_feeling': float(avg_feeling) if avg_feeling else None,
                'avg_satisfaction': float(avg_satisfaction) if avg_satisfaction else None
            }

            return render_template_string(
                DASHBOARD_HTML,
                clients=client_data,
                jobs=jobs,
                responses=responses,
                latest_responses=latest_responses[:3],
                stats=stats,
                now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
