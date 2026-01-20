"""Admin dashboard web routes with secure authentication"""

import os
import secrets
import hashlib
from functools import wraps
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template_string, redirect, url_for, session, flash
from src.utils.logger import setup_logger
from src.database.session import get_session, db_transaction
from src.models.workspace import Workspace
from src.models.client import Client
from src.models.standup_response import StandupResponse
from src.models.feedback_response import FeedbackResponse
from src.services.scheduler_service import get_scheduled_jobs, get_scheduler

logger = setup_logger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Generate a random admin secret on first run if not set
ADMIN_SECRET = os.environ.get('ADMIN_DASHBOARD_SECRET')


def require_admin_auth(f):
    """Decorator to require admin authentication for dashboard routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check session-based auth first
        if session.get('admin_authenticated'):
            return f(*args, **kwargs)

        # Check for token in header (API access)
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
            if ADMIN_SECRET and secrets.compare_digest(token, ADMIN_SECRET):
                return f(*args, **kwargs)

        # Not authenticated - redirect to login
        return redirect(url_for('admin.login'))

    return decorated_function


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if not ADMIN_SECRET:
        return render_template_string(DASHBOARD_TEMPLATE,
            page='error',
            error_message="Admin dashboard is not configured. Set ADMIN_DASHBOARD_SECRET environment variable.")

    if request.method == 'POST':
        password = request.form.get('password', '')
        if secrets.compare_digest(password, ADMIN_SECRET):
            session['admin_authenticated'] = True
            session.permanent = True
            logger.info("Admin dashboard login successful")
            return redirect(url_for('admin.dashboard'))
        else:
            logger.warning("Admin dashboard login failed")
            return render_template_string(LOGIN_TEMPLATE, error="Invalid password")

    return render_template_string(LOGIN_TEMPLATE, error=None)


@admin_bp.route('/logout')
def logout():
    """Admin logout"""
    session.pop('admin_authenticated', None)
    return redirect(url_for('admin.login'))


@admin_bp.route('/')
@require_admin_auth
def dashboard():
    """Main admin dashboard"""
    db_session = get_session()
    try:
        # Get workspace info
        workspace = db_session.query(Workspace).first()

        # Get client stats
        total_clients = db_session.query(Client).count()
        active_clients = db_session.query(Client).filter_by(is_active=True).count()

        # Get response stats for last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        standup_count = db_session.query(StandupResponse).filter(
            StandupResponse.submitted_at >= week_ago
        ).count()
        feedback_count = db_session.query(FeedbackResponse).filter(
            FeedbackResponse.submitted_at >= week_ago
        ).count()

        # Get scheduler info
        scheduler = get_scheduler()
        scheduler_status = "running" if scheduler and scheduler.running else "stopped"
        scheduled_jobs = get_scheduled_jobs() if scheduler else []

        return render_template_string(DASHBOARD_TEMPLATE,
            page='dashboard',
            workspace=workspace,
            total_clients=total_clients,
            active_clients=active_clients,
            standup_count=standup_count,
            feedback_count=feedback_count,
            scheduler_status=scheduler_status,
            job_count=len(scheduled_jobs)
        )
    finally:
        db_session.close()


@admin_bp.route('/clients')
@require_admin_auth
def clients():
    """Client management page"""
    db_session = get_session()
    try:
        clients_list = db_session.query(Client).order_by(Client.created_at.desc()).all()

        # Enrich with config info
        client_data = []
        for client in clients_list:
            client_data.append({
                'id': client.id,
                'slack_user_id': client.slack_user_id,
                'display_name': client.display_name,
                'email': client.email,
                'timezone': client.timezone,
                'is_active': client.is_active,
                'created_at': client.created_at,
                'standup_config': {
                    'schedule_type': client.standup_config.schedule_type if client.standup_config else None,
                    'schedule_time': str(client.standup_config.schedule_time) if client.standup_config else None,
                    'is_paused': client.standup_config.is_paused if client.standup_config else None
                },
                'feedback_config': {
                    'is_enabled': client.feedback_config.is_enabled if client.feedback_config else False,
                    'schedule_time': str(client.feedback_config.schedule_time) if client.feedback_config else None
                }
            })

        return render_template_string(DASHBOARD_TEMPLATE,
            page='clients',
            clients=client_data
        )
    finally:
        db_session.close()


@admin_bp.route('/analytics')
@require_admin_auth
def analytics():
    """Analytics and reporting page"""
    db_session = get_session()
    try:
        # Get standup stats by day for last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        standup_responses = db_session.query(StandupResponse).filter(
            StandupResponse.submitted_at >= thirty_days_ago
        ).all()

        feedback_responses = db_session.query(FeedbackResponse).filter(
            FeedbackResponse.submitted_at >= thirty_days_ago
        ).all()

        # Calculate average satisfaction rating
        if feedback_responses:
            avg_satisfaction = sum(f.satisfaction_rating or 3 for f in feedback_responses) / len(feedback_responses)
            avg_feeling = sum(f.feeling_rating or 3 for f in feedback_responses) / len(feedback_responses)
        else:
            avg_satisfaction = 0
            avg_feeling = 0

        # Calculate response rates
        total_clients = db_session.query(Client).filter_by(is_active=True).count()

        return render_template_string(DASHBOARD_TEMPLATE,
            page='analytics',
            standup_count=len(standup_responses),
            feedback_count=len(feedback_responses),
            avg_satisfaction=round(avg_satisfaction, 1),
            avg_feeling=round(avg_feeling, 1),
            total_clients=total_clients
        )
    finally:
        db_session.close()


@admin_bp.route('/jobs')
@require_admin_auth
def jobs():
    """Scheduled jobs page"""
    scheduled_jobs = get_scheduled_jobs()
    scheduler = get_scheduler()

    return render_template_string(DASHBOARD_TEMPLATE,
        page='jobs',
        jobs=scheduled_jobs,
        scheduler_running=scheduler.running if scheduler else False
    )


@admin_bp.route('/settings')
@require_admin_auth
def settings():
    """Settings page"""
    db_session = get_session()
    try:
        workspace = db_session.query(Workspace).first()

        return render_template_string(DASHBOARD_TEMPLATE,
            page='settings',
            workspace=workspace,
            admin_ids=workspace.admin_user_ids if workspace else []
        )
    finally:
        db_session.close()


# API endpoints for AJAX operations
@admin_bp.route('/api/clients/<int:client_id>/toggle-pause', methods=['POST'])
@require_admin_auth
def api_toggle_pause(client_id):
    """Toggle client standup pause status"""
    from src.services.client_service import pause_client_standups, resume_client_standups, get_client

    client = get_client(client_id)
    if not client:
        return jsonify({'error': 'Client not found'}), 404

    if client.standup_config and client.standup_config.is_paused:
        success = resume_client_standups(client_id)
        action = 'resumed'
    else:
        success = pause_client_standups(client_id)
        action = 'paused'

    if success:
        return jsonify({'success': True, 'action': action})
    return jsonify({'error': 'Failed to update client'}), 500


@admin_bp.route('/api/clients/<int:client_id>', methods=['DELETE'])
@require_admin_auth
def api_delete_client(client_id):
    """Delete a client"""
    from src.services.client_service import remove_client

    success = remove_client(client_id)
    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to delete client'}), 500


@admin_bp.route('/api/health')
def api_health():
    """API health check (no auth required)"""
    db_session = get_session()
    try:
        # Test database
        db_session.execute("SELECT 1")
        db_ok = True
    except:
        db_ok = False
    finally:
        db_session.close()

    scheduler = get_scheduler()
    scheduler_ok = scheduler and scheduler.running

    return jsonify({
        'status': 'ok' if db_ok and scheduler_ok else 'degraded',
        'database': 'connected' if db_ok else 'error',
        'scheduler': 'running' if scheduler_ok else 'stopped',
        'timestamp': datetime.utcnow().isoformat()
    })


# HTML Templates
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Login - Vibe Check</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-card {
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 400px;
        }
        h1 { color: #333; margin-bottom: 8px; text-align: center; }
        .subtitle { color: #666; margin-bottom: 30px; text-align: center; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 6px; color: #555; font-weight: 500; }
        input[type="password"] {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.2s;
        }
        input[type="password"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        .error {
            background: #fee;
            color: #c00;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="login-card">
        <h1>Vibe Check</h1>
        <p class="subtitle">Admin Dashboard</p>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <div class="form-group">
                <label for="password">Admin Password</label>
                <input type="password" id="password" name="password" placeholder="Enter admin password" required autofocus>
            </div>
            <button type="submit">Sign In</button>
        </form>
    </div>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - Vibe Check</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            min-height: 100vh;
        }
        .sidebar {
            position: fixed;
            left: 0;
            top: 0;
            bottom: 0;
            width: 240px;
            background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: white;
        }
        .sidebar h1 {
            font-size: 24px;
            margin-bottom: 8px;
        }
        .sidebar .subtitle {
            font-size: 12px;
            opacity: 0.8;
            margin-bottom: 30px;
        }
        .nav-link {
            display: block;
            padding: 12px 16px;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            margin-bottom: 4px;
            transition: background 0.2s;
        }
        .nav-link:hover, .nav-link.active {
            background: rgba(255,255,255,0.2);
        }
        .nav-link.active {
            background: rgba(255,255,255,0.3);
            font-weight: 600;
        }
        .logout-link {
            position: absolute;
            bottom: 20px;
            left: 20px;
            right: 20px;
        }
        .main-content {
            margin-left: 240px;
            padding: 30px;
        }
        .page-header {
            margin-bottom: 30px;
        }
        .page-header h2 {
            color: #333;
            font-size: 28px;
        }
        .page-header p {
            color: #666;
            margin-top: 4px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .stat-card .label {
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
        }
        .stat-card .value {
            font-size: 32px;
            font-weight: 700;
            color: #333;
        }
        .stat-card .value.green { color: #28a745; }
        .stat-card .value.blue { color: #667eea; }
        .stat-card .value.orange { color: #fd7e14; }
        .card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 20px;
        }
        .card h3 {
            color: #333;
            margin-bottom: 16px;
            font-size: 18px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th {
            font-weight: 600;
            color: #666;
            font-size: 12px;
            text-transform: uppercase;
        }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge.green { background: #d4edda; color: #155724; }
        .badge.yellow { background: #fff3cd; color: #856404; }
        .badge.red { background: #f8d7da; color: #721c24; }
        .badge.blue { background: #cce5ff; color: #004085; }
        .btn {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            cursor: pointer;
            border: none;
            transition: all 0.2s;
        }
        .btn-primary {
            background: #667eea;
            color: white;
        }
        .btn-primary:hover {
            background: #5a6fd6;
        }
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        .btn-danger:hover {
            background: #c82333;
        }
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        .btn-sm {
            padding: 4px 10px;
            font-size: 12px;
        }
        .alert {
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .alert-warning {
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeeba;
        }
        .alert-info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }
        .empty-state h3 {
            color: #333;
            margin-bottom: 8px;
        }
    </style>
</head>
<body>
    <nav class="sidebar">
        <h1>Vibe Check</h1>
        <p class="subtitle">Admin Dashboard</p>

        <a href="{{ url_for('admin.dashboard') }}" class="nav-link {% if page == 'dashboard' %}active{% endif %}">
            Dashboard
        </a>
        <a href="{{ url_for('admin.clients') }}" class="nav-link {% if page == 'clients' %}active{% endif %}">
            Clients
        </a>
        <a href="{{ url_for('admin.analytics') }}" class="nav-link {% if page == 'analytics' %}active{% endif %}">
            Analytics
        </a>
        <a href="{{ url_for('admin.jobs') }}" class="nav-link {% if page == 'jobs' %}active{% endif %}">
            Scheduled Jobs
        </a>
        <a href="{{ url_for('admin.settings') }}" class="nav-link {% if page == 'settings' %}active{% endif %}">
            Settings
        </a>

        <a href="{{ url_for('admin.logout') }}" class="nav-link logout-link">
            Logout
        </a>
    </nav>

    <main class="main-content">
        {% if page == 'error' %}
        <div class="page-header">
            <h2>Configuration Error</h2>
        </div>
        <div class="alert alert-warning">
            {{ error_message }}
        </div>

        {% elif page == 'dashboard' %}
        <div class="page-header">
            <h2>Dashboard</h2>
            <p>Overview of your Vibe Check installation</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">Total Clients</div>
                <div class="value blue">{{ total_clients }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Active Clients</div>
                <div class="value green">{{ active_clients }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Standups (7 days)</div>
                <div class="value">{{ standup_count }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Feedback (7 days)</div>
                <div class="value">{{ feedback_count }}</div>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">Scheduler Status</div>
                <div class="value {% if scheduler_status == 'running' %}green{% else %}red{% endif %}">
                    {{ scheduler_status|title }}
                </div>
            </div>
            <div class="stat-card">
                <div class="label">Scheduled Jobs</div>
                <div class="value">{{ job_count }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Workspace</div>
                <div class="value" style="font-size: 18px;">{{ workspace.team_name if workspace else 'Not configured' }}</div>
            </div>
        </div>

        {% elif page == 'clients' %}
        <div class="page-header">
            <h2>Client Management</h2>
            <p>Manage clients receiving standups and feedback</p>
        </div>

        {% if clients %}
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Slack ID</th>
                        <th>Timezone</th>
                        <th>Schedule</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for client in clients %}
                    <tr>
                        <td>
                            <strong>{{ client.display_name or 'Unknown' }}</strong>
                            {% if client.email %}
                            <br><small style="color: #666;">{{ client.email }}</small>
                            {% endif %}
                        </td>
                        <td><code>{{ client.slack_user_id }}</code></td>
                        <td>{{ client.timezone }}</td>
                        <td>
                            {% if client.standup_config.schedule_type %}
                            {{ client.standup_config.schedule_type|title }} @ {{ client.standup_config.schedule_time }}
                            {% else %}
                            Not configured
                            {% endif %}
                        </td>
                        <td>
                            {% if not client.is_active %}
                            <span class="badge red">Inactive</span>
                            {% elif client.standup_config.is_paused %}
                            <span class="badge yellow">Paused</span>
                            {% else %}
                            <span class="badge green">Active</span>
                            {% endif %}
                        </td>
                        <td>
                            <button class="btn btn-secondary btn-sm" onclick="togglePause({{ client.id }})">
                                {{ 'Resume' if client.standup_config.is_paused else 'Pause' }}
                            </button>
                            <button class="btn btn-danger btn-sm" onclick="deleteClient({{ client.id }}, '{{ client.display_name }}')">
                                Delete
                            </button>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% else %}
        <div class="card empty-state">
            <h3>No Clients Yet</h3>
            <p>Use the <code>/vibe-add-client</code> command in Slack to add clients.</p>
        </div>
        {% endif %}

        {% elif page == 'analytics' %}
        <div class="page-header">
            <h2>Analytics</h2>
            <p>Insights from the last 30 days</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">Total Standups</div>
                <div class="value blue">{{ standup_count }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Total Feedback</div>
                <div class="value blue">{{ feedback_count }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Avg Satisfaction</div>
                <div class="value {% if avg_satisfaction >= 4 %}green{% elif avg_satisfaction >= 3 %}orange{% else %}red{% endif %}">
                    {{ avg_satisfaction }}/5
                </div>
            </div>
            <div class="stat-card">
                <div class="label">Avg Feeling</div>
                <div class="value {% if avg_feeling >= 4 %}green{% elif avg_feeling >= 3 %}orange{% else %}red{% endif %}">
                    {{ avg_feeling }}/5
                </div>
            </div>
        </div>

        <div class="card">
            <h3>Response Metrics</h3>
            <p style="color: #666; margin-top: 8px;">
                With {{ total_clients }} active clients, you received {{ standup_count }} standups
                and {{ feedback_count }} feedback responses in the last 30 days.
            </p>
        </div>

        {% elif page == 'jobs' %}
        <div class="page-header">
            <h2>Scheduled Jobs</h2>
            <p>APScheduler job management</p>
        </div>

        <div class="card">
            <h3>Scheduler Status:
                <span class="badge {% if scheduler_running %}green{% else %}red{% endif %}">
                    {{ 'Running' if scheduler_running else 'Stopped' }}
                </span>
            </h3>
        </div>

        {% if jobs %}
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th>Job ID</th>
                        <th>Name</th>
                        <th>Next Run</th>
                        <th>Trigger</th>
                    </tr>
                </thead>
                <tbody>
                    {% for job in jobs %}
                    <tr>
                        <td><code>{{ job.id }}</code></td>
                        <td>{{ job.name }}</td>
                        <td>{{ job.next_run.strftime('%Y-%m-%d %H:%M:%S UTC') if job.next_run else 'Not scheduled' }}</td>
                        <td><small>{{ job.trigger }}</small></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% else %}
        <div class="card empty-state">
            <h3>No Scheduled Jobs</h3>
            <p>Jobs will appear here once clients are added.</p>
        </div>
        {% endif %}

        {% elif page == 'settings' %}
        <div class="page-header">
            <h2>Settings</h2>
            <p>Workspace configuration</p>
        </div>

        <div class="card">
            <h3>Workspace Information</h3>
            <table>
                <tr>
                    <td><strong>Team Name</strong></td>
                    <td>{{ workspace.team_name if workspace else 'Not configured' }}</td>
                </tr>
                <tr>
                    <td><strong>Team ID</strong></td>
                    <td><code>{{ workspace.team_id if workspace else 'N/A' }}</code></td>
                </tr>
                <tr>
                    <td><strong>Vibe Check Channel</strong></td>
                    <td>
                        {% if workspace and workspace.vibe_check_channel_id %}
                        <code>{{ workspace.vibe_check_channel_id }}</code>
                        {% else %}
                        <span class="badge yellow">Not Set</span>
                        <small>Use <code>/vibe-set-channel</code> in Slack</small>
                        {% endif %}
                    </td>
                </tr>
            </table>
        </div>

        <div class="card">
            <h3>Admin Users</h3>
            {% if admin_ids %}
            <ul style="padding-left: 20px;">
                {% for admin_id in admin_ids %}
                <li><code>{{ admin_id }}</code></li>
                {% endfor %}
            </ul>
            <p style="color: #666; margin-top: 12px; font-size: 14px;">
                Add admins using <code>/vibe-admin add @username</code> in Slack
            </p>
            {% else %}
            <p style="color: #666;">No admins configured</p>
            {% endif %}
        </div>

        {% endif %}
    </main>

    <script>
    function togglePause(clientId) {
        fetch('/admin/api/clients/' + clientId + '/toggle-pause', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            alert('Error: ' + error.message);
        });
    }

    function deleteClient(clientId, name) {
        if (!confirm('Are you sure you want to delete ' + name + '? This cannot be undone.')) {
            return;
        }

        fetch('/admin/api/clients/' + clientId, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            alert('Error: ' + error.message);
        });
    }
    </script>
</body>
</html>
'''
