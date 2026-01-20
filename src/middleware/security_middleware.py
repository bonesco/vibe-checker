"""Security middleware for production deployment"""

import time
import os
from functools import wraps
from collections import defaultdict
from threading import Lock
from flask import request, jsonify, Response
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window.

    For production at scale, consider using Redis-based rate limiting.
    """

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # seconds
        self.requests = defaultdict(list)
        self.lock = Lock()

    def is_rate_limited(self, key: str) -> bool:
        """Check if a key (IP or user) is rate limited"""
        now = time.time()
        window_start = now - self.window_size

        with self.lock:
            # Clean old requests
            self.requests[key] = [
                timestamp for timestamp in self.requests[key]
                if timestamp > window_start
            ]

            # Check if over limit
            if len(self.requests[key]) >= self.requests_per_minute:
                return True

            # Record this request
            self.requests[key].append(now)
            return False

    def get_remaining(self, key: str) -> int:
        """Get remaining requests for a key"""
        now = time.time()
        window_start = now - self.window_size

        with self.lock:
            current = len([
                t for t in self.requests[key]
                if t > window_start
            ])
            return max(0, self.requests_per_minute - current)


# Global rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=120)


def setup_security_middleware(app):
    """
    Configure security middleware for Flask app.

    Adds:
    - Security headers (HSTS, XSS protection, etc.)
    - Rate limiting
    - Request logging
    """

    @app.before_request
    def security_checks():
        """Run security checks before each request"""
        # Skip rate limiting for health checks and static files
        if request.path in ['/health', '/']:
            return None

        # Get client identifier for rate limiting
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip:
            client_ip = client_ip.split(',')[0].strip()

        # Check rate limit
        if rate_limiter.is_rate_limited(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.'
            }), 429

        # Log request (exclude sensitive headers)
        log_request(request)

    @app.after_request
    def add_security_headers(response: Response) -> Response:
        """Add security headers to all responses"""

        # Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "frame-ancestors 'none';"
        )

        # Prevent XSS attacks
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # HTTPS enforcement (HSTS)
        # Only enable in production (when using HTTPS)
        if os.environ.get('RAILWAY_STATIC_URL') or os.environ.get('ENABLE_HSTS'):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # Referrer policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions policy (formerly Feature-Policy)
        response.headers['Permissions-Policy'] = (
            'accelerometer=(), camera=(), geolocation=(), gyroscope=(), '
            'magnetometer=(), microphone=(), payment=(), usb=()'
        )

        # Add rate limit headers
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip:
            client_ip = client_ip.split(',')[0].strip()
            remaining = rate_limiter.get_remaining(client_ip)
            response.headers['X-RateLimit-Limit'] = str(rate_limiter.requests_per_minute)
            response.headers['X-RateLimit-Remaining'] = str(remaining)

        return response

    logger.info("Security middleware configured")


def log_request(req):
    """Log request information (excluding sensitive data)"""
    # Don't log Slack events payload (too verbose)
    if req.path == '/slack/events':
        return

    logger.info(f"Request: {req.method} {req.path} from {req.headers.get('X-Forwarded-For', req.remote_addr)}")


def require_https(f):
    """
    Decorator to require HTTPS for sensitive endpoints.

    Redirects HTTP to HTTPS in production.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if we're behind a proxy (Railway, Heroku, etc.)
        if request.headers.get('X-Forwarded-Proto') == 'http':
            # Only enforce in production
            if os.environ.get('RAILWAY_STATIC_URL') or os.environ.get('ENFORCE_HTTPS'):
                url = request.url.replace('http://', 'https://', 1)
                return redirect(url, code=301)
        return f(*args, **kwargs)
    return decorated_function


def sanitize_input(value: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent injection attacks.

    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not value:
        return ""

    # Truncate to max length
    value = value[:max_length]

    # Remove null bytes
    value = value.replace('\x00', '')

    # Remove control characters (except newlines and tabs)
    import re
    value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)

    return value.strip()


def validate_slack_signature(signing_secret: str, timestamp: str, body: bytes, signature: str) -> bool:
    """
    Validate Slack request signature.

    This is handled automatically by Slack Bolt, but included here for reference
    or manual validation needs.

    Args:
        signing_secret: Slack signing secret
        timestamp: X-Slack-Request-Timestamp header
        body: Raw request body
        signature: X-Slack-Signature header

    Returns:
        True if signature is valid
    """
    import hmac
    import hashlib

    # Check timestamp is recent (within 5 minutes)
    import time
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False

    # Compute signature
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    computed_signature = 'v0=' + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    # Compare signatures
    return hmac.compare_digest(computed_signature, signature)
