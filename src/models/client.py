"""Client model - represents users receiving standups and feedback requests"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from src.models.base import Base, TimestampMixin


class Client(Base, TimestampMixin):
    """
    Client user receiving standups and feedback requests

    Each client belongs to a workspace and has individual configurations
    """

    __tablename__ = 'clients'

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False, index=True)
    slack_user_id = Column(String(20), nullable=False, index=True)
    display_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    timezone = Column(String(50), default='UTC', nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    workspace = relationship('Workspace', back_populates='clients')
    standup_config = relationship('StandupConfig', back_populates='client', uselist=False, cascade='all, delete-orphan')
    feedback_config = relationship('FeedbackConfig', back_populates='client', uselist=False, cascade='all, delete-orphan')
    standup_responses = relationship('StandupResponse', back_populates='client', cascade='all, delete-orphan')
    feedback_responses = relationship('FeedbackResponse', back_populates='client', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Client(id={self.id}, slack_user_id='{self.slack_user_id}', display_name='{self.display_name}')>"

    @property
    def job_id_standup(self) -> str:
        """Generate unique job ID for standup scheduling"""
        return f"standup_{self.workspace_id}_{self.id}"

    @property
    def job_id_feedback(self) -> str:
        """Generate unique job ID for feedback scheduling"""
        return f"feedback_{self.workspace_id}_{self.id}"
