"""Feedback configuration model"""

from sqlalchemy import Column, Integer, Boolean, ForeignKey, Time, JSON
from sqlalchemy.orm import relationship
from src.models.base import Base, TimestampMixin


class FeedbackConfig(Base, TimestampMixin):
    """
    Weekly feedback configuration for a client

    Defines when to send Friday feedback requests
    """

    __tablename__ = 'feedback_configs'

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id', ondelete='CASCADE'), unique=True, nullable=False)
    schedule_time = Column(Time, default='15:00:00', nullable=False)  # Friday time
    is_enabled = Column(Boolean, default=True, nullable=False)
    custom_questions = Column(JSON, nullable=True)  # Optional custom question overrides

    # Relationships
    client = relationship('Client', back_populates='feedback_config')

    def __repr__(self):
        return f"<FeedbackConfig(id={self.id}, client_id={self.client_id}, enabled={self.is_enabled}, time={self.schedule_time})>"

    @property
    def is_active(self) -> bool:
        """Check if this feedback config is active"""
        return self.is_enabled and self.client.is_active
