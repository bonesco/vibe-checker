#!/usr/bin/env python3
"""Initialize database schema"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database.session import init_db
from src.config import validate_environment
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    """Initialize the database"""
    logger.info("Starting database initialization...")

    # Validate environment
    if not validate_environment():
        logger.error("Environment validation failed")
        sys.exit(1)

    try:
        # Create all tables
        init_db()
        logger.info("Database initialized successfully!")
        logger.info("Tables created:")
        logger.info("  - workspaces")
        logger.info("  - clients")
        logger.info("  - standup_configs")
        logger.info("  - feedback_configs")
        logger.info("  - standup_responses")
        logger.info("  - feedback_responses")
        logger.info("  - apscheduler_jobs (created automatically by APScheduler)")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
