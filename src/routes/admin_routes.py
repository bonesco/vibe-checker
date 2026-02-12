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
        from sqlalchemy import text
        db_session.execute(text("SELECT 1"))
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
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .nav-brand {
            font-weight: 600;
            font-size: 15px;
            color: #fafafa;
            text-decoration: none;
            display: inline-flex;
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
        .login-card {
            width: 100%;
            max-width: 360px;
        }
        h1 {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 8px;
            letter-spacing: -0.02em;
        }
        .subtitle {
            color: #888;
            font-size: 15px;
            margin-bottom: 32px;
        }
        .form-group { margin-bottom: 20px; }
        label {
            display: block;
            margin-bottom: 8px;
            color: #888;
            font-size: 13px;
            font-weight: 500;
        }
        input[type="password"] {
            width: 100%;
            padding: 12px 16px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            font-size: 15px;
            color: #fafafa;
            font-family: inherit;
            transition: border-color 0.15s;
        }
        input[type="password"]:focus {
            outline: none;
            border-color: rgba(255,255,255,0.3);
        }
        input[type="password"]::placeholder {
            color: #666;
        }
        button {
            width: 100%;
            padding: 12px;
            background: #fafafa;
            color: #0a0a0a;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            font-family: inherit;
            transition: background 0.15s;
        }
        button:hover {
            background: #e5e5e5;
        }
        .error {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.2);
            color: #fca5a5;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
            font-size: 14px;
        }
        .back-link {
            display: block;
            text-align: center;
            margin-top: 24px;
            color: #666;
            font-size: 13px;
            text-decoration: none;
        }
        .back-link:hover { color: #888; }
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
        <div class="login-card">
            <h1>Admin Dashboard</h1>
            <p class="subtitle">Enter your password to continue</p>
            {% if error %}
            <div class="error">{{ error }}</div>
            {% endif %}
            <form method="POST">
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" placeholder="Enter admin password" required autofocus>
                </div>
                <button type="submit">Sign in</button>
            </form>
            <a href="/" class="back-link">Back to home</a>
        </div>
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
            -webkit-font-smoothing: antialiased;
        }
        .sidebar {
            position: fixed;
            left: 0;
            top: 0;
            bottom: 0;
            width: 220px;
            background: #0a0a0a;
            border-right: 1px solid rgba(255,255,255,0.1);
            padding: 20px 12px;
            display: flex;
            flex-direction: column;
        }
        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 12px;
            margin-bottom: 24px;
            text-decoration: none;
            color: #fafafa;
        }
        .sidebar-brand span { font-weight: 600; font-size: 15px; }
        .nav-section {
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 8px 12px;
            margin-top: 16px;
        }
        .nav-link {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            color: #888;
            text-decoration: none;
            border-radius: 6px;
            font-size: 14px;
            transition: all 0.15s;
        }
        .nav-link:hover { color: #fafafa; background: rgba(255,255,255,0.05); }
        .nav-link.active { color: #fafafa; background: rgba(255,255,255,0.1); }
        .nav-link svg { width: 16px; height: 16px; opacity: 0.7; }
        .sidebar-footer {
            margin-top: auto;
            padding-top: 16px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }
        .main-content {
            margin-left: 220px;
            min-height: 100vh;
        }
        .top-bar {
            padding: 16px 32px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .page-title { font-size: 14px; font-weight: 500; }
        .content { padding: 32px; }
        .page-header { margin-bottom: 32px; }
        .page-header h2 {
            font-size: 24px;
            font-weight: 600;
            letter-spacing: -0.02em;
            margin-bottom: 4px;
        }
        .page-header p { color: #888; font-size: 14px; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }
        .stat-card {
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 20px;
        }
        .stat-card .label {
            font-size: 13px;
            color: #666;
            margin-bottom: 8px;
        }
        .stat-card .value {
            font-size: 28px;
            font-weight: 600;
            letter-spacing: -0.02em;
        }
        .stat-card .value.green { color: #22c55e; }
        .stat-card .value.blue { color: #3b82f6; }
        .stat-card .value.orange { color: #f97316; }
        .stat-card .value.red { color: #ef4444; }
        .card {
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            margin-bottom: 20px;
            overflow: hidden;
        }
        .card-header {
            padding: 16px 20px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            font-size: 14px;
            font-weight: 500;
        }
        .card-body { padding: 20px; }
        table { width: 100%; border-collapse: collapse; }
        th, td {
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        th {
            font-weight: 500;
            color: #666;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        td { font-size: 14px; }
        code {
            background: rgba(255,255,255,0.1);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 13px;
        }
        .badge {
            display: inline-flex;
            align-items: center;
            padding: 4px 10px;
            border-radius: 100px;
            font-size: 12px;
            font-weight: 500;
        }
        .badge.green { background: rgba(34,197,94,0.1); color: #22c55e; }
        .badge.yellow { background: rgba(234,179,8,0.1); color: #eab308; }
        .badge.red { background: rgba(239,68,68,0.1); color: #ef4444; }
        .badge.blue { background: rgba(59,130,246,0.1); color: #3b82f6; }
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            text-decoration: none;
            cursor: pointer;
            border: none;
            transition: all 0.15s;
            font-family: inherit;
        }
        .btn-primary { background: #fafafa; color: #0a0a0a; }
        .btn-primary:hover { background: #e5e5e5; }
        .btn-secondary {
            background: transparent;
            color: #888;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .btn-secondary:hover { color: #fafafa; border-color: rgba(255,255,255,0.4); }
        .btn-danger { background: rgba(239,68,68,0.1); color: #ef4444; }
        .btn-danger:hover { background: rgba(239,68,68,0.2); }
        .btn-sm { padding: 6px 10px; font-size: 12px; }
        .alert {
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .alert-warning {
            background: rgba(234,179,8,0.1);
            color: #eab308;
            border: 1px solid rgba(234,179,8,0.2);
        }
        .alert-info {
            background: rgba(59,130,246,0.1);
            color: #3b82f6;
            border: 1px solid rgba(59,130,246,0.2);
        }
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }
        .empty-state h3 { color: #888; margin-bottom: 8px; font-size: 16px; }
        .empty-state p { font-size: 14px; }
        @media (max-width: 768px) {
            .sidebar { width: 100%; position: relative; border-right: none; border-bottom: 1px solid rgba(255,255,255,0.1); }
            .main-content { margin-left: 0; }
        }
    </style>
</head>
<body>
    <nav class="sidebar">
        <a href="/" class="sidebar-brand">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
            <span>Vibe Check</span>
        </a>

        <div class="nav-section">Overview</div>
        <a href="{{ url_for('admin.dashboard') }}" class="nav-link {% if page == 'dashboard' %}active{% endif %}">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
            Dashboard
        </a>
        <a href="{{ url_for('admin.analytics') }}" class="nav-link {% if page == 'analytics' %}active{% endif %}">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 20V10M12 20V4M6 20v-6"/></svg>
            Analytics
        </a>

        <div class="nav-section">Manage</div>
        <a href="{{ url_for('admin.clients') }}" class="nav-link {% if page == 'clients' %}active{% endif %}">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            Clients
        </a>
        <a href="{{ url_for('admin.jobs') }}" class="nav-link {% if page == 'jobs' %}active{% endif %}">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            Jobs
        </a>
        <a href="{{ url_for('admin.settings') }}" class="nav-link {% if page == 'settings' %}active{% endif %}">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            Settings
        </a>

        <div class="sidebar-footer">
            <a href="{{ url_for('admin.logout') }}" class="nav-link">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>
                Logout
            </a>
        </div>
    </nav>

    <main class="main-content">
        <div class="top-bar">
            <span class="page-title">{% if page == 'dashboard' %}Dashboard{% elif page == 'clients' %}Clients{% elif page == 'analytics' %}Analytics{% elif page == 'jobs' %}Scheduled Jobs{% elif page == 'settings' %}Settings{% endif %}</span>
        </div>

        <div class="content">
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
        </div>
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
