"""Workspace model - represents a Slack workspace/team"""

from sqlalchemy import Column, Integer, String, Boolean, ARRAY, Text
from sqlalchemy.orm import relationship
from src.models.base import Base, TimestampMixin


class Workspace(Base, TimestampMixin):
    """
    Slack workspace with installed app

    Stores workspace info and encrypted bot token for multi-workspace support
    """

    __tablename__ = 'workspaces'

    id = Column(Integer, primary_key=True)
    team_id = Column(String(20), unique=True, nullable=False, index=True)
    team_name = Column(String(255), nullable=False)
    bot_token = Column(Text, nullable=False)  # Encrypted with Fernet
    bot_user_id = Column(String(20), nullable=False)
    scope = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    vibe_check_channel_id = Column(String(20), nullable=True)  # Private feedback channel
    admin_user_ids = Column(ARRAY(String), nullable=True)  # List of admin user IDs

    # Relationships
    clients = relationship('Client', back_populates='workspace', cascade='all, delete-orphan')
    standup_responses = relationship('StandupResponse', back_populates='workspace', cascade='all, delete-orphan')
    feedback_responses = relationship('FeedbackResponse', back_populates='workspace', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Workspace(id={self.id}, team_id='{self.team_id}', team_name='{self.team_name}')>"

    def is_admin(self, user_id: str) -> bool:
        """Check if user is an admin for this workspace"""
        return user_id in (self.admin_user_ids or [])
