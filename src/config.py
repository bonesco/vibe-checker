"""Configuration management for Vibe Check Slack App"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Application configuration from environment variables"""

    # Required - Slack Configuration
    SLACK_CLIENT_ID: str
    SLACK_CLIENT_SECRET: str
    SLACK_SIGNING_SECRET: str

    # Required - Database Configuration
    DATABASE_URL: str

    # Required - Security
    ENCRYPTION_KEY: str

    # Optional - Slack
    SLACK_BOT_TOKEN: Optional[str] = None  # Not needed for multi-workspace

    # Optional - Application Settings
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    RAILWAY_STATIC_URL: Optional[str] = None

    # Optional - Feature Flags
    ENABLE_REMINDERS: bool = True
    REMINDER_DELAY_HOURS: int = 4
    DATA_RETENTION_DAYS: int = 90

    @classmethod
    def from_env(cls):
        """Create config from environment variables"""
        return cls(
            # Slack
            SLACK_CLIENT_ID=os.getenv('SLACK_CLIENT_ID', ''),
            SLACK_CLIENT_SECRET=os.getenv('SLACK_CLIENT_SECRET', ''),
            SLACK_SIGNING_SECRET=os.getenv('SLACK_SIGNING_SECRET', ''),
            SLACK_BOT_TOKEN=os.getenv('SLACK_BOT_TOKEN'),

            # Database
            DATABASE_URL=os.getenv('DATABASE_URL', ''),

            # Security
            ENCRYPTION_KEY=os.getenv('ENCRYPTION_KEY', ''),

            # Application
            PORT=int(os.getenv('PORT', '8000')),
            LOG_LEVEL=os.getenv('LOG_LEVEL', 'INFO'),
            RAILWAY_STATIC_URL=os.getenv('RAILWAY_STATIC_URL'),

            # Features
            ENABLE_REMINDERS=os.getenv('ENABLE_REMINDERS', 'true').lower() == 'true',
            REMINDER_DELAY_HOURS=int(os.getenv('REMINDER_DELAY_HOURS', '4')),
            DATA_RETENTION_DAYS=int(os.getenv('DATA_RETENTION_DAYS', '90'))
        )

    def validate(self):
        """Validate required configuration values"""
        required_vars = {
            'SLACK_CLIENT_ID': self.SLACK_CLIENT_ID,
            'SLACK_CLIENT_SECRET': self.SLACK_CLIENT_SECRET,
            'SLACK_SIGNING_SECRET': self.SLACK_SIGNING_SECRET,
            'DATABASE_URL': self.DATABASE_URL,
            'ENCRYPTION_KEY': self.ENCRYPTION_KEY,
        }

        missing = [name for name, value in required_vars.items() if not value]

        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please check your .env file or environment configuration."
            )

        # Validate encryption key format
        if self.ENCRYPTION_KEY:
            try:
                from cryptography.fernet import Fernet
                Fernet(self.ENCRYPTION_KEY.encode())
            except Exception as e:
                raise EnvironmentError(
                    f"Invalid ENCRYPTION_KEY format: {e}\n"
                    f"Generate a valid key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                )


# Global config instance
config = Config.from_env()


def validate_environment():
    """Validate environment configuration at startup"""
    try:
        config.validate()
        return True
    except EnvironmentError as e:
        print(f"❌ Configuration Error: {e}")
        return False
