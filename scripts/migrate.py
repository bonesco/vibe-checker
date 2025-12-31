#!/usr/bin/env python3
"""Run database migrations"""

import sys
import os
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.config import validate_environment
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    """Run Alembic migrations"""
    logger.info("Running database migrations...")

    # Validate environment
    if not validate_environment():
        logger.error("Environment validation failed")
        sys.exit(1)

    try:
        # Run alembic upgrade head
        result = subprocess.run(
            ['alembic', 'upgrade', 'head'],
            check=True,
            capture_output=True,
            text=True
        )

        logger.info("Migration output:")
        logger.info(result.stdout)

        if result.stderr:
            logger.warning(f"Migration warnings: {result.stderr}")

        logger.info("Database migrations completed successfully!")

    except subprocess.CalledProcessError as e:
        logger.error(f"Migration failed: {e}")
        logger.error(f"Output: {e.stdout}")
        logger.error(f"Error: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
