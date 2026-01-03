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
        if not config.ADMIN_API_KEY:
            return """<!DOCTYPE html>
<html><head><title>NOT CONFIGURED</title>
<style>
body{font-family:'SF Mono',monospace;max-width:480px;margin:100px auto;padding:2rem}
h1{font-size:1.5rem;margin-bottom:1rem}
code{background:#f5f5f5;padding:0.25rem 0.5rem;border:1px solid #e0e0e0}
</style></head>
<body>
<h1>ADMIN NOT CONFIGURED</h1>
<p>Set <code>ADMIN_API_KEY</code> environment variable.</p>
<p style="margin-top:1rem">Generate key:</p>
<code>python -c "import secrets; print(secrets.token_urlsafe(32))"</code>
</body></html>""", 503

        provided_key = request.headers.get('X-Admin-Key') or request.args.get('key')

        if not provided_key:
            return """<!DOCTYPE html>
<html><head><title>AUTH REQUIRED</title>
<style>
body{font-family:'SF Mono',monospace;max-width:480px;margin:100px auto;padding:2rem}
h1{font-size:1.5rem;margin-bottom:1rem}
code{background:#f5f5f5;padding:0.25rem 0.5rem;border:1px solid #e0e0e0}
</style></head>
<body>
<h1>AUTHENTICATION REQUIRED</h1>
<p>Add <code>?key=YOUR_KEY</code> to URL</p>
</body></html>""", 401

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

    for env_var in ['SLACK_BOT_TOKEN', 'SLACK_CLIENT_ID', 'SLACK_CLIENT_SECRET']:
        if env_var in os.environ:
            del os.environ[env_var]

    app = App(
        token=bot_token,
        signing_secret=signing_secret
    )

    logger.info("Slack app created successfully")
    return app


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Vibe Check</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            background: #f8f8f8;
            color: #111;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 32px; }

        /* Header */
        header {
            background: #fff;
            border-bottom: 1px solid #eee;
            padding: 16px 32px;
        }
        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .logo-icon {
            width: 28px;
            height: 28px;
            background: #111;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .logo-icon span {
            color: #fff;
            font-weight: 600;
            font-size: 14px;
        }
        header h1 {
            font-size: 15px;
            font-weight: 600;
            color: #111;
        }
        .header-actions {
            display: flex;
            gap: 16px;
            align-items: center;
        }
        .auto-refresh {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
            color: #666;
        }
        .auto-refresh input { accent-color: #111; }

        /* Stats */
        .stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 32px;
        }
        .stat-card {
            background: #fff;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.04);
        }
        .stat-card .label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #888;
            margin-bottom: 8px;
            font-weight: 500;
        }
        .stat-card .value {
            font-size: 36px;
            font-weight: 600;
            letter-spacing: -0.03em;
            color: #111;
        }
        .stat-card .subtext {
            font-size: 12px;
            color: #999;
            margin-top: 4px;
        }

        /* Cards */
        .card {
            background: #fff;
            border-radius: 12px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.04);
            overflow: hidden;
        }
        .card-header {
            padding: 20px 24px;
            border-bottom: 1px solid #f0f0f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .card-header h2 {
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #111;
        }
        .card-body { padding: 0; }

        /* Grid */
        .grid-2 {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 24px;
        }

        /* Table */
        table { width: 100%; border-collapse: collapse; }
        th, td {
            padding: 16px 24px;
            text-align: left;
            border-bottom: 1px solid #f5f5f5;
            font-size: 14px;
        }
        th {
            font-weight: 500;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #888;
        }
        tr:last-child td { border-bottom: none; }
        tr:hover { background: #fafafa; }

        /* Badges */
        .badge {
            display: inline-block;
            padding: 5px 10px;
            font-size: 11px;
            font-weight: 500;
            border-radius: 6px;
        }
        .badge-active { background: #e8f5e9; color: #2e7d32; }
        .badge-paused { background: #f5f5f5; color: #666; }
        .badge-standup { background: #e3f2fd; color: #1565c0; }
        .badge-vibe { background: #f3e5f5; color: #7b1fa2; }

        /* Buttons */
        .btn {
            display: inline-block;
            padding: 8px 14px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background: #fff;
            color: #333;
            font-family: inherit;
            font-size: 13px;
            font-weight: 500;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.15s;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        }
        .btn:hover { background: #fafafa; border-color: #ccc; }
        .btn-sm { padding: 6px 10px; font-size: 12px; }

        /* Client */
        .client-info { display: flex; align-items: center; gap: 12px; }
        .client-avatar {
            width: 36px;
            height: 36px;
            background: #111;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 13px;
            color: #fff;
        }
        .client-name { font-weight: 500; color: #111; }
        .client-meta { font-size: 13px; color: #888; }

        /* Schedule */
        .schedule-item {
            font-size: 13px;
            color: #666;
            margin-bottom: 4px;
        }
        .schedule-item:last-child { margin-bottom: 0; }

        /* Empty */
        .empty-state {
            padding: 48px 24px;
            text-align: center;
            color: #888;
            font-size: 14px;
        }
        .empty-state code {
            background: #f5f5f5;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 13px;
            color: #555;
        }

        /* Tabs */
        .tabs { display: flex; gap: 4px; }
        .tab {
            padding: 7px 14px;
            border: none;
            background: transparent;
            border-radius: 6px;
            font-family: inherit;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            color: #888;
            transition: all 0.15s;
        }
        .tab:hover { color: #111; background: #f5f5f5; }
        .tab.active { color: #111; background: #f0f0f0; }

        /* Response Card */
        .response-card {
            background: #fafafa;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 24px;
            margin-top: 0;
        }
        .response-card:first-child { margin-top: 20px; }
        .response-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .response-header strong { color: #111; }
        .response-label {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #999;
            margin-bottom: 6px;
            font-weight: 500;
        }
        .response-content {
            font-size: 14px;
            color: #444;
            line-height: 1.6;
        }
        .response-section { margin-bottom: 16px; }
        .response-section:last-child { margin-bottom: 0; }

        /* Responsive */
        @media (max-width: 1024px) {
            .stats { grid-template-columns: repeat(2, 1fr); }
            .grid-2 { grid-template-columns: 1fr; }
        }
        @media (max-width: 640px) {
            .stats { grid-template-columns: 1fr; }
            .header-content { flex-direction: column; gap: 16px; }
            .container { padding: 20px; }
        }
    </style>
</head>
<body>
    <header>
        <div class="header-content">
            <div class="logo">
                <div class="logo-icon"><span>V</span></div>
                <h1>Vibe Check</h1>
            </div>
            <div class="header-actions">
                <label class="auto-refresh">
                    <input type="checkbox" id="autoRefresh" onchange="toggleAutoRefresh()">
                    Auto-refresh
                </label>
                <a href="/admin?key={{ request.args.get('key', '') }}" class="btn btn-sm">Refresh</a>
            </div>
        </div>
    </header>

    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <div class="label">Clients</div>
                <div class="value">{{ stats.total_clients }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Active</div>
                <div class="value">{{ stats.active_clients }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Avg Feeling</div>
                <div class="value">{{ '%.1f' | format(stats.avg_feeling) if stats.avg_feeling else '—' }}</div>
                <div class="subtext">7-day average</div>
            </div>
            <div class="stat-card">
                <div class="label">Satisfaction</div>
                <div class="value">{{ '%.1f' | format(stats.avg_satisfaction) if stats.avg_satisfaction else '—' }}</div>
                <div class="subtext">7-day average</div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <h2>Clients</h2>
                <div class="tabs">
                    <button class="tab active" onclick="showTab('all')">All ({{ clients|length }})</button>
                    <button class="tab" onclick="showTab('active')">Active</button>
                    <button class="tab" onclick="showTab('paused')">Paused</button>
                </div>
            </div>
            <div class="card-body">
                {% if clients %}
                <table>
                    <thead>
                        <tr>
                            <th>Client</th>
                            <th>Schedule</th>
                            <th>Next Run</th>
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
                                    <div>
                                        <div class="client-name">{{ client.display_name }}</div>
                                        <div class="client-meta">{{ client.timezone }}</div>
                                    </div>
                                </div>
                            </td>
                            <td>
                                {% if client.standup_schedule %}
                                <div class="schedule-item">{{ client.standup_schedule }}</div>
                                {% endif %}
                                {% if client.vibe_check_enabled %}
                                <div class="schedule-item">Fridays @ {{ client.vibe_check_time }}</div>
                                {% endif %}
                                {% if not client.standup_schedule and not client.vibe_check_enabled %}
                                <span style="color:#ccc">—</span>
                                {% endif %}
                            </td>
                            <td style="color:#888">{{ client.next_run if client.next_run else '—' }}</td>
                            <td>
                                {% if client.is_paused %}
                                <span class="badge badge-paused">Paused</span>
                                {% elif client.is_active %}
                                <span class="badge badge-active">Active</span>
                                {% else %}
                                <span class="badge badge-paused">Inactive</span>
                                {% endif %}
                            </td>
                            <td>
                                {% if client.standup_schedule %}
                                <a href="/admin/send/standup/{{ client.id }}?key={{ request.args.get('key', '') }}" class="btn btn-sm" onclick="return confirm('Send standup now?')">Standup</a>
                                {% endif %}
                                {% if client.vibe_check_enabled %}
                                <a href="/admin/send/feedback/{{ client.id }}?key={{ request.args.get('key', '') }}" class="btn btn-sm" onclick="return confirm('Send vibe check now?')">Vibe</a>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <div class="empty-state">
                    <p>No clients yet. Use <code>/vibe-add-client</code> in Slack.</p>
                </div>
                {% endif %}
            </div>
        </div>

        <div class="grid-2">
            <div class="card">
                <div class="card-header">
                    <h2>Recent Responses</h2>
                </div>
                <div class="card-body">
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
                                <td><span class="badge badge-{{ 'standup' if response.type == 'standup' else 'vibe' }}">{{ response.type }}</span></td>
                                <td>{{ response.rating ~ '/5' if response.rating else '—' }}</td>
                                <td style="color:#888">{{ response.date }}</td>
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
                    <h2>Scheduled Jobs</h2>
                </div>
                <div class="card-body">
                    {% if jobs %}
                    <table>
                        <thead>
                            <tr>
                                <th>Type</th>
                                <th>Next Run</th>
                                <th>Trigger</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for job in jobs %}
                            <tr>
                                <td><span class="badge badge-{{ 'standup' if 'standup' in job.id else 'vibe' }}">{{ 'standup' if 'standup' in job.id else 'vibe' }}</span></td>
                                <td>{{ job.next_run_formatted or '—' }}</td>
                                <td style="color:#888;font-size:12px">{{ job.trigger }}</td>
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
                <h2>Latest Responses</h2>
            </div>
            <div class="card-body">
                {% for res in latest_responses %}
                <div class="response-card">
                    <div class="response-header">
                        <strong>{{ res.client_name }}</strong>
                        <span class="badge badge-{{ 'standup' if res.type == 'standup' else 'vibe' }}">{{ res.type }}</span>
                    </div>
                    {% if res.accomplishments %}
                    <div class="response-section">
                        <div class="response-label">Completed</div>
                        <div class="response-content">{{ res.accomplishments }}</div>
                    </div>
                    {% endif %}
                    {% if res.working_on %}
                    <div class="response-section">
                        <div class="response-label">In Progress</div>
                        <div class="response-content">{{ res.working_on }}</div>
                    </div>
                    {% endif %}
                    {% if res.blockers %}
                    <div class="response-section">
                        <div class="response-label">Blockers</div>
                        <div class="response-content">{{ res.blockers }}</div>
                    </div>
                    {% endif %}
                    {% if res.feeling_text %}
                    <div class="response-section">
                        <div class="response-label">Notes</div>
                        <div class="response-content">{{ res.feeling_text }}</div>
                    </div>
                    {% endif %}
                    {% if res.improvements %}
                    <div class="response-section">
                        <div class="response-label">Improvements</div>
                        <div class="response-content">{{ res.improvements }}</div>
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
    </div>

    <script>
        let refreshInterval;
        function toggleAutoRefresh() {
            const checkbox = document.getElementById('autoRefresh');
            if (checkbox.checked) {
                refreshInterval = setInterval(() => location.reload(), 30000);
            } else {
                clearInterval(refreshInterval);
            }
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
        return handler.handle(request)

    @flask_app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint for Railway"""
        return jsonify({"status": "ok"}), 200

    @flask_app.route("/", methods=["GET"])
    def home():
        """Home page"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VIBE CHECK</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
            background: #fff;
            color: #000;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 2rem;
        }
        .container { max-width: 480px; margin: 0 auto; }
        h1 {
            font-size: 2.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 2rem;
            line-height: 1;
        }
        .status {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #000;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .status::before {
            content: '';
            width: 6px;
            height: 6px;
            background: #000;
            display: inline-block;
        }
        .divider {
            width: 100%;
            height: 1px;
            background: #000;
            margin: 2rem 0;
        }
        .command {
            font-size: 0.875rem;
            color: #666;
        }
        .command code {
            background: #f5f5f5;
            padding: 0.25rem 0.5rem;
            border: 1px solid #e0e0e0;
        }
    </style>
</head>
<body>
    <div class="container">
        <p class="status">System Active</p>
        <h1>VIBE CHECK</h1>
        <div class="divider"></div>
        <p class="command">Run <code>/vibe-help</code> in Slack</p>
    </div>
</body>
</html>"""

    @flask_app.route("/admin", methods=["GET"])
    @require_admin_auth
    def admin_dashboard():
        """Admin dashboard"""
        from datetime import timedelta
        from src.database.session import get_session
        from src.models.client import Client
        from src.models.standup_response import StandupResponse
        from src.models.feedback_response import FeedbackResponse

        try:
            from src.services.scheduler_service import scheduler
            jobs = []
            if scheduler and scheduler.running:
                for job in scheduler.get_jobs():
                    jobs.append({
                        'id': job.id,
                        'next_run_formatted': job.next_run_time.strftime('%b %d, %H:%M') if job.next_run_time else None,
                        'trigger': str(job.trigger)
                    })
        except:
            jobs = []

        with get_session() as session:
            clients = session.query(Client).all()

            client_list = []
            for client in clients:
                standup_schedule = None
                vibe_check_enabled = False
                vibe_check_time = None
                is_paused = False
                next_run = None

                if client.standup_config:
                    schedule_type = "Daily" if client.standup_config.schedule_type == "daily" else "Weekly"
                    time_str = client.standup_config.schedule_time.strftime('%H:%M')
                    standup_schedule = f"{schedule_type} @ {time_str}"
                    is_paused = client.standup_config.is_paused

                if client.feedback_config and client.feedback_config.is_enabled:
                    vibe_check_enabled = True
                    vibe_check_time = client.feedback_config.schedule_time.strftime('%H:%M') if client.feedback_config.schedule_time else '15:00'

                for job in jobs:
                    if str(client.id) in job['id']:
                        next_run = job['next_run_formatted']
                        break

                client_list.append({
                    'id': client.id,
                    'display_name': client.display_name or client.slack_user_id,
                    'timezone': client.timezone,
                    'standup_schedule': standup_schedule,
                    'vibe_check_enabled': vibe_check_enabled,
                    'vibe_check_time': vibe_check_time,
                    'is_active': client.is_active,
                    'is_paused': is_paused,
                    'next_run': next_run
                })

            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)

            responses_today = (
                session.query(StandupResponse).filter(StandupResponse.submitted_at >= today_start).count() +
                session.query(FeedbackResponse).filter(FeedbackResponse.submitted_at >= today_start).count()
            )

            recent_feedback = session.query(FeedbackResponse).filter(
                FeedbackResponse.submitted_at >= week_ago
            ).all()

            avg_feeling = None
            avg_satisfaction = None
            if recent_feedback:
                feelings = [f.feeling_rating for f in recent_feedback if f.feeling_rating]
                satisfactions = [f.satisfaction_rating for f in recent_feedback if f.satisfaction_rating]
                if feelings:
                    avg_feeling = sum(feelings) / len(feelings)
                if satisfactions:
                    avg_satisfaction = sum(satisfactions) / len(satisfactions)

            stats = {
                'total_clients': len(clients),
                'active_clients': len([c for c in client_list if c['is_active'] and not c['is_paused']]),
                'scheduled_jobs': len(jobs),
                'responses_today': responses_today,
                'avg_feeling': avg_feeling,
                'avg_satisfaction': avg_satisfaction
            }

            recent_standups = session.query(StandupResponse).order_by(
                StandupResponse.submitted_at.desc()
            ).limit(5).all()

            recent_vibes = session.query(FeedbackResponse).order_by(
                FeedbackResponse.submitted_at.desc()
            ).limit(5).all()

            responses = []
            for s in recent_standups:
                client = session.query(Client).filter_by(id=s.client_id).first()
                responses.append({
                    'client_name': client.display_name if client else 'Unknown',
                    'type': 'standup',
                    'rating': None,
                    'date': s.submitted_at.strftime('%b %d')
                })

            for f in recent_vibes:
                client = session.query(Client).filter_by(id=f.client_id).first()
                responses.append({
                    'client_name': client.display_name if client else 'Unknown',
                    'type': 'vibe',
                    'rating': f.feeling_rating,
                    'date': f.submitted_at.strftime('%b %d')
                })

            responses.sort(key=lambda x: x['date'], reverse=True)
            responses = responses[:10]

            latest_responses = []
            for s in recent_standups[:3]:
                client = session.query(Client).filter_by(id=s.client_id).first()
                latest_responses.append({
                    'client_name': client.display_name if client else 'Unknown',
                    'type': 'standup',
                    'accomplishments': s.accomplishments,
                    'working_on': s.working_on,
                    'blockers': s.blockers,
                    'feeling_text': None,
                    'improvements': None
                })

            for f in recent_vibes[:3]:
                client = session.query(Client).filter_by(id=f.client_id).first()
                latest_responses.append({
                    'client_name': client.display_name if client else 'Unknown',
                    'type': 'vibe',
                    'accomplishments': None,
                    'working_on': None,
                    'blockers': f.blockers,
                    'feeling_text': f.feeling_text,
                    'improvements': f.improvements
                })

        return render_template_string(
            DASHBOARD_HTML,
            stats=stats,
            clients=client_list,
            responses=responses,
            jobs=jobs,
            latest_responses=latest_responses[:5]
        )

    @flask_app.route("/admin/send/standup/<int:client_id>", methods=["GET"])
    @require_admin_auth
    def send_standup(client_id):
        """Manually send standup to a client"""
        from src.services.standup_service import send_standup_to_client
        from src.database.session import get_session
        from src.models.client import Client

        with get_session() as session:
            client = session.query(Client).filter_by(id=client_id).first()
            if not client:
                return jsonify({"error": "Client not found"}), 404

            try:
                send_standup_to_client(client_id)
                key = request.args.get('key', '')
                return f"""<!DOCTYPE html>
<html><head><meta http-equiv="refresh" content="2;url=/admin?key={key}"></head>
<body style="font-family:monospace;padding:2rem">
<p>STANDUP SENT — Redirecting...</p>
</body></html>"""
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    @flask_app.route("/admin/send/feedback/<int:client_id>", methods=["GET"])
    @require_admin_auth
    def send_feedback(client_id):
        """Manually send feedback request to a client"""
        from src.services.feedback_service import send_feedback_to_client
        from src.database.session import get_session
        from src.models.client import Client

        with get_session() as session:
            client = session.query(Client).filter_by(id=client_id).first()
            if not client:
                return jsonify({"error": "Client not found"}), 404

            try:
                send_feedback_to_client(client_id)
                key = request.args.get('key', '')
                return f"""<!DOCTYPE html>
<html><head><meta http-equiv="refresh" content="2;url=/admin?key={key}"></head>
<body style="font-family:monospace;padding:2rem">
<p>VIBE CHECK SENT — Redirecting...</p>
</body></html>"""
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    logger.info("Flask app configured")
    return flask_app
