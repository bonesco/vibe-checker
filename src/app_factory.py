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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            background: #fafafa;
            color: #111;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 24px; }

        /* Header - Clean white */
        header {
            background: #fff;
            border-bottom: 1px solid #eaeaea;
            padding: 20px 0;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 24px;
        }
        .header-left { display: flex; align-items: center; gap: 12px; }
        .logo {
            width: 32px;
            height: 32px;
        }
        .logo svg {
            width: 100%;
            height: 100%;
        }
        header h1 { font-size: 16px; font-weight: 600; letter-spacing: -0.02em; }
        .header-actions { display: flex; gap: 12px; align-items: center; }
        .auto-refresh {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
            color: #666;
        }
        .auto-refresh input {
            cursor: pointer;
            accent-color: #000;
        }

        /* Stats Grid */
        .stats {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 16px;
            margin-bottom: 32px;
        }
        .stat-card {
            background: #fff;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04);
            transition: box-shadow 0.2s ease;
        }
        .stat-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.1), 0 2px 4px rgba(0,0,0,0.04);
        }
        .stat-card .label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }
        .stat-card .value {
            font-size: 28px;
            font-weight: 600;
            color: #111;
            letter-spacing: -0.02em;
        }
        .stat-card .subtext {
            font-size: 12px;
            color: #888;
            margin-top: 4px;
        }

        /* Cards */
        .grid-2 {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 24px;
        }
        .card {
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04);
            margin-bottom: 24px;
            overflow: hidden;
        }
        .card-header {
            padding: 16px 20px;
            border-bottom: 1px solid #eaeaea;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .card-header h2 {
            font-size: 14px;
            font-weight: 600;
            color: #111;
            letter-spacing: -0.01em;
        }
        .card-body { padding: 20px; }
        .card-body.compact { padding: 0; }

        /* Table */
        table { width: 100%; border-collapse: collapse; }
        th, td {
            padding: 14px 20px;
            text-align: left;
            border-bottom: 1px solid #eaeaea;
        }
        th {
            font-weight: 500;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #666;
            background: #fafafa;
        }
        tr:last-child td { border-bottom: none; }
        tr:hover { background: #fafafa; }

        /* Badges */
        .badge {
            display: inline-flex;
            align-items: center;
            padding: 4px 10px;
            border-radius: 100px;
            font-size: 12px;
            font-weight: 500;
        }
        .badge-success { background: #e8f5e9; color: #2e7d32; }
        .badge-warning { background: #fff8e1; color: #f57c00; }
        .badge-info { background: #e3f2fd; color: #1565c0; }
        .badge-danger { background: #ffebee; color: #c62828; }
        .badge-secondary { background: #f5f5f5; color: #616161; }
        .badge-purple { background: #f3e5f5; color: #7b1fa2; }

        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 8px 16px;
            border: 1px solid #eaeaea;
            border-radius: 8px;
            background: #fff;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            color: #111;
            text-decoration: none;
            transition: all 0.15s ease;
        }
        .btn:hover {
            background: #fafafa;
            border-color: #ddd;
        }
        .btn-primary {
            background: #000;
            color: #fff;
            border-color: #000;
        }
        .btn-primary:hover {
            background: #333;
            border-color: #333;
        }
        .btn-sm { padding: 6px 10px; font-size: 12px; border-radius: 6px; }
        .actions { display: flex; gap: 6px; }

        /* Client Avatar */
        .client-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: #111;
            color: #fff;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-weight: 500;
            font-size: 14px;
            margin-right: 12px;
        }
        .client-info { display: flex; align-items: center; }
        .client-details { display: flex; flex-direction: column; }
        .client-name { font-weight: 500; font-size: 14px; }
        .client-meta { font-size: 12px; color: #666; }

        /* Schedule Info */
        .schedule-info { display: flex; flex-direction: column; gap: 4px; }
        .schedule-item {
            font-size: 13px;
            color: #444;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .schedule-item .icon {
            font-size: 12px;
            opacity: 0.7;
        }

        /* Tabs */
        .tab-container { display: flex; gap: 4px; }
        .tab {
            padding: 6px 12px;
            border: none;
            background: transparent;
            cursor: pointer;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            color: #666;
            transition: all 0.15s ease;
        }
        .tab:hover { background: #f5f5f5; color: #111; }
        .tab.active { background: #111; color: #fff; }

        /* Response Preview */
        .response-preview {
            background: #fafafa;
            border: 1px solid #eaeaea;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
        }
        .response-preview:last-child { margin-bottom: 0; }
        .response-preview .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .response-preview .client-name { font-weight: 500; font-size: 14px; }
        .response-preview .label {
            font-size: 11px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #888;
            margin-bottom: 4px;
            margin-top: 12px;
        }
        .response-preview .label:first-of-type { margin-top: 0; }
        .response-preview .content {
            color: #444;
            font-size: 13px;
            line-height: 1.6;
        }

        /* Rating Display */
        .rating-display {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 13px;
        }

        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 48px 24px;
            color: #666;
        }
        .empty-state p { font-size: 14px; }
        .empty-state code {
            background: #f5f5f5;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 13px;
        }

        /* Footer */
        .footer-note {
            text-align: center;
            color: #888;
            font-size: 12px;
            margin-top: 32px;
            padding-bottom: 24px;
        }

        /* Tooltip */
        .tooltip { position: relative; cursor: default; }
        .tooltip:hover::after {
            content: attr(data-tooltip);
            position: absolute;
            bottom: calc(100% + 4px);
            left: 50%;
            transform: translateX(-50%);
            background: #111;
            color: #fff;
            padding: 6px 10px;
            border-radius: 6px;
            font-size: 12px;
            white-space: nowrap;
            z-index: 100;
        }

        /* Responsive */
        @media (max-width: 1024px) {
            .stats { grid-template-columns: repeat(3, 1fr); }
            .grid-2 { grid-template-columns: 1fr; }
        }
        @media (max-width: 768px) {
            .stats { grid-template-columns: repeat(2, 1fr); }
            .header-content { flex-direction: column; gap: 12px; align-items: flex-start; }
            th, td { padding: 10px 14px; }
            .container { padding: 16px; }
        }
    </style>
</head>
<body>
    <header>
        <div class="header-content">
            <div class="header-left">
                <div class="logo"><svg viewBox="0 0 1432 1432" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="716" cy="716" r="716" fill="black"/><path d="M243.891 664.964C175.739 646.602 152.614 610.239 160.835 517.592C171.725 386.046 175.672 363.115 180.157 346.467C190.109 309.53 216.245 295.368 254.223 305.6C286.998 314.431 299.5 338.445 294.791 374.563L269.183 560.735L274.386 562.136L345.775 388.3C359.848 354.705 382.723 340.222 415.498 349.052C453.476 359.285 468.959 384.661 459.007 421.598C454.522 438.246 446.414 460.056 389.742 579.267C350.306 663.503 312.042 683.326 243.891 664.964Z" fill="white"/><path d="M611.529 453.909C572.044 462.505 549.263 446.511 538.833 398.602L494.02 192.755C483.591 144.847 497.662 120.83 537.146 112.234C577.158 103.523 599.939 119.518 610.369 167.426L655.182 373.273C665.612 421.181 651.541 445.199 611.529 453.909Z" fill="white"/><path d="M819.438 480.53C712.037 440.086 697.178 422.976 735.533 321.121L779.395 204.645C807.117 131.027 843.335 115.879 948.215 155.374C1019.82 182.336 1064.66 222.253 1041.68 283.264C1028.96 317.048 1005.8 334.232 973.631 337.088C1005.38 362.861 1012.9 393.33 997.713 433.668C968.092 512.328 900.619 511.1 819.438 480.53ZM856.89 393.304C872.017 399.001 887.287 392.085 892.983 376.958C898.87 361.327 892.144 345.552 877.017 339.856C861.89 334.16 846.43 341.58 840.544 357.211C834.847 372.338 841.763 387.608 856.89 393.304ZM897.334 285.904C910.444 290.84 923.822 284.363 928.948 270.749C933.885 257.639 927.912 244.451 914.803 239.514C901.693 234.578 888.505 240.55 883.568 253.66C878.441 267.275 884.224 280.967 897.334 285.904Z" fill="white"/><path d="M1226.19 660.742C1147.94 684.919 1114.44 665.944 1088.2 581.005L1054.32 471.357C1028.39 387.447 1045.34 352.885 1123.59 328.708L1175.07 312.802C1222.43 298.168 1247.95 307.764 1259.4 344.828C1270.54 380.863 1256.62 401.518 1213.89 414.72L1164.47 429.99L1172.74 456.758L1236.06 437.194C1262.32 429.082 1277.5 436.234 1284.81 459.914C1291.81 482.564 1283.15 496.518 1256.9 504.63L1193.58 524.195L1202.49 553.022L1251.91 537.753C1294.63 524.551 1318.1 534.783 1329.23 570.818C1340.68 607.882 1325.02 630.202 1277.66 644.836L1226.19 660.742Z" fill="white"/><path d="M298.724 1046.57C218.406 1077.89 148.795 1040.26 106.518 931.832C64.2397 823.403 92.8826 751.513 176.714 718.826C249.502 690.445 306.655 710.955 330.926 773.201C348.346 817.878 322.166 836.76 300.581 845.177C276.988 854.376 260.609 850.931 243.463 832.171C231.371 818.958 223.586 816.789 216.056 819.725C202.502 825.01 201.066 840.606 220.247 889.801C239.233 938.493 250.848 949.001 264.402 943.716C271.931 940.78 276.194 933.913 276.15 916.003C276.071 890.588 285.796 876.965 309.389 867.766C330.974 859.35 363.025 855.527 380.25 899.702C404.52 961.948 374.523 1017.02 298.724 1046.57Z" fill="white"/><path d="M630.232 890.211C589.912 887.526 572.457 865.843 575.715 816.921L579.367 762.086L540.66 759.508L537.008 814.343C533.749 863.265 513.572 882.441 472.714 879.72C432.394 877.034 414.939 855.352 418.197 806.43L432.198 596.227C435.456 547.305 455.633 528.129 495.953 530.815C536.811 533.536 554.267 555.218 551.008 604.14L546.425 672.953L585.132 675.531L589.716 606.718C592.974 557.796 613.151 538.621 653.471 541.306C694.329 544.027 711.785 565.71 708.526 614.632L694.526 824.835C691.267 873.757 671.09 892.932 630.232 890.211Z" fill="white"/><path d="M806.726 894.412C732.05 860.786 719.481 824.4 755.982 743.338L803.102 638.694C839.161 558.614 874.738 543.907 949.413 577.532L998.542 599.654C1043.74 620.007 1056.53 644.085 1040.61 679.458C1025.12 713.848 1001.02 720.131 960.242 701.77L913.078 680.533L901.575 706.08L962.003 733.29C987.059 744.572 993.713 759.977 983.536 782.576C973.803 804.193 958.079 808.931 933.023 797.648L872.595 770.438L860.207 797.95L907.37 819.187C948.147 837.549 958.975 860.742 943.49 895.132C927.562 930.505 901.053 936.886 855.855 916.534L806.726 894.412Z" fill="white"/><path d="M1034.62 977.66C980.329 910.698 994.966 832.934 1085.36 759.638C1175.76 686.342 1252.96 691.726 1309.63 761.618C1358.83 822.302 1356.71 882.986 1304.81 925.064C1267.56 955.264 1241.61 936.08 1227.01 918.084C1211.06 898.414 1209.36 881.764 1222 859.719C1230.9 844.177 1230.6 836.101 1225.51 829.824C1216.35 818.524 1201.05 821.906 1160.04 855.16C1119.44 888.076 1112.97 902.339 1122.14 913.639C1127.23 919.917 1135.07 921.885 1152.11 916.388C1176.29 908.572 1192.23 913.684 1208.18 933.354C1222.77 951.351 1236.18 980.714 1199.35 1010.58C1147.45 1052.65 1085.86 1040.86 1034.62 977.66Z" fill="white"/><path d="M715.169 1267.24C690.585 1275.27 674.79 1266.83 631.571 1228.24L573.946 1176.78L571.898 1177.45L590.64 1234.81C606.38 1281.25 595.838 1306.23 556.914 1318.95C518.503 1331.5 494.219 1317.89 478.991 1271.29L413.561 1071.04C398.333 1024.43 409.9 999.114 448.311 986.563C487.235 973.845 510.494 987.785 525.21 1034.56L548.805 1106.77L550.341 1106.27L558.5 1023.68C564.29 966.807 573.276 945.732 601.444 936.529C636.27 925.15 665.656 940.489 675.027 969.169C681.051 987.607 678.211 1006.67 671.903 1035.94L657.878 1102.31L709.763 1144.87C732.992 1163.92 747.91 1176.62 754.771 1197.62C763.808 1225.27 752.043 1255.19 715.169 1267.24Z" fill="white"/><path d="M893.718 1177.07C859.613 1167 852.247 1146.28 860.073 1106.46L875.362 1026.15C886.063 970.878 913.928 958.32 953.717 970.069C992.473 981.512 1009.56 1007.35 988.528 1059.56L958.254 1135.45C943.193 1173.14 926.273 1186.68 893.718 1177.07ZM854.175 1305.28C820.587 1295.36 804.869 1264.88 815.092 1230.26C824.857 1197.19 854.155 1181.68 887.743 1191.6C921.331 1201.52 937.506 1230.45 927.741 1263.52C917.518 1298.14 887.763 1315.2 854.175 1305.28Z" fill="white"/></svg></div>
                <h1>Vibe Check</h1>
            </div>
            <div class="header-actions">
                <label class="auto-refresh">
                    <input type="checkbox" id="autoRefresh" onchange="toggleAutoRefresh()">
                    Auto-refresh
                </label>
                <a href="/admin/refresh?key={{ request.args.get('key', '') }}" class="btn">Refresh</a>
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
                <div class="label">Scheduled</div>
                <div class="value">{{ stats.scheduled_jobs }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Today</div>
                <div class="value">{{ stats.responses_today }}</div>
                <div class="subtext">responses</div>
            </div>
            <div class="stat-card">
                <div class="label">Avg Feeling</div>
                <div class="value">{{ '%.1f' | format(stats.avg_feeling) if stats.avg_feeling else '–' }}</div>
                <div class="subtext">7-day avg</div>
            </div>
            <div class="stat-card">
                <div class="label">Satisfaction</div>
                <div class="value">{{ '%.1f' | format(stats.avg_satisfaction) if stats.avg_satisfaction else '–' }}</div>
                <div class="subtext">7-day avg</div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <h2>Clients</h2>
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
                                        <span class="icon">◉</span>
                                        <span>{{ client.standup_schedule }}</span>
                                    </div>
                                    {% endif %}
                                    {% if client.vibe_check_enabled %}
                                    <div class="schedule-item">
                                        <span class="icon">◉</span>
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
                                    <span style="color:#999">–</span>
                                {% endif %}
                            </td>
                            <td>
                                {% if client.is_paused %}
                                    <span class="badge badge-warning">Paused</span>
                                {% elif client.is_active %}
                                    <span class="badge badge-success">Active</span>
                                {% else %}
                                    <span class="badge badge-danger">Inactive</span>
                                {% endif %}
                            </td>
                            <td class="actions">
                                {% if client.standup_schedule %}
                                <a href="/admin/send/standup/{{ client.id }}?key={{ request.args.get('key', '') }}" class="btn btn-sm" onclick="return confirm('Send standup to {{ client.display_name }} now?')" title="Send Standup">Standup</a>
                                {% endif %}
                                {% if client.vibe_check_enabled %}
                                <a href="/admin/send/feedback/{{ client.id }}?key={{ request.args.get('key', '') }}" class="btn btn-sm" onclick="return confirm('Send vibe check to {{ client.display_name }} now?')" title="Send Vibe Check">Vibe</a>
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
                    <h2>Recent Responses</h2>
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
                                <td style="font-weight:500">{{ response.client_name }}</td>
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
                                    <span style="color:#999">–</span>
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
                    <h2>Scheduled Jobs</h2>
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
                                        <span class="badge badge-info">Standup</span>
                                    {% else %}
                                        <span class="badge badge-purple">Vibe Check</span>
                                    {% endif %}
                                </td>
                                <td>{{ job.next_run_formatted or 'Not scheduled' }}</td>
                                <td><span style="color:#666;font-size:12px">{{ job.trigger }}</span></td>
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
                {% for resp in latest_responses[:3] %}
                <div class="response-preview">
                    <div class="header">
                        <span class="client-name">{{ resp.client_name }}</span>
                        <span class="badge badge-{{ 'info' if resp.type == 'standup' else 'purple' }}">
                            {{ 'Standup' if resp.type == 'standup' else 'Vibe Check' }} · {{ resp.date }}
                        </span>
                    </div>
                    {% if resp.type == 'standup' %}
                        {% if resp.accomplishments %}
                        <div class="label">Accomplishments</div>
                        <div class="content">{{ resp.accomplishments }}</div>
                        {% endif %}
                        {% if resp.working_on %}
                        <div class="label">Today's Focus</div>
                        <div class="content">{{ resp.working_on }}</div>
                        {% endif %}
                    {% else %}
                        {% if resp.feeling_text %}
                        <div class="label">What went well</div>
                        <div class="content">{{ resp.feeling_text }}</div>
                        {% endif %}
                        {% if resp.improvements %}
                        <div class="label">Improvements</div>
                        <div class="content">{{ resp.improvements }}</div>
                        {% endif %}
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <p class="footer-note">
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
                    el.textContent = ` · refreshing in ${remaining}s`;
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
