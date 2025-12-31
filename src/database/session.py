"""Database session management"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
from src.config import config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Create engine - use different settings for SQLite vs PostgreSQL
if config.DATABASE_URL.startswith('sqlite'):
    # SQLite doesn't support connection pooling the same way
    engine = create_engine(
        config.DATABASE_URL,
        connect_args={"check_same_thread": False},  # Allow multi-threaded access
        echo=False
    )
else:
    # PostgreSQL with connection pooling
    engine = create_engine(
        config.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Thread-safe session
Session = scoped_session(SessionLocal)


def get_session():
    """
    Get a new database session

    Returns:
        SQLAlchemy session instance

    Example:
        >>> session = get_session()
        >>> workspace = session.query(Workspace).first()
        >>> session.close()
    """
    return SessionLocal()


@contextmanager
def db_transaction():
    """
    Context manager for database transactions with automatic commit/rollback

    Yields:
        SQLAlchemy session

    Example:
        >>> with db_transaction() as session:
        ...     client = Client(slack_user_id='U123', workspace_id=1)
        ...     session.add(client)
        ...     # Automatically commits if no exception, rolls back otherwise
    """
    session = get_session()
    try:
        yield session
        session.commit()
        logger.info("Database transaction committed")
    except Exception as e:
        session.rollback()
        logger.error(f"Database transaction failed, rolled back: {e}")
        raise
    finally:
        session.close()


def init_db():
    """
    Initialize database schema

    Creates all tables defined in models
    """
    from src.models.base import Base
    # Import all models to ensure they're registered
    from src.models.workspace import Workspace
    from src.models.client import Client
    from src.models.standup_config import StandupConfig
    from src.models.feedback_config import FeedbackConfig
    from src.models.standup_response import StandupResponse
    from src.models.feedback_response import FeedbackResponse

    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
