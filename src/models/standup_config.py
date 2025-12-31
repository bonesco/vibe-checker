"""Standup configuration model"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Time, JSON
from sqlalchemy.orm import relationship
from src.models.base import Base, TimestampMixin


class StandupConfig(Base, TimestampMixin):
    """
    Standup schedule configuration for a client

    Defines when and how often to send standup requests
    """

    __tablename__ = 'standup_configs'

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id', ondelete='CASCADE'), unique=True, nullable=False)
    schedule_type = Column(String(20), nullable=False)  # 'daily' or 'monday_only'
    schedule_time = Column(Time, nullable=False)  # Time to send standup (e.g., 09:00:00)
    is_paused = Column(Boolean, default=False, nullable=False)
    custom_questions = Column(JSON, nullable=True)  # Optional custom question overrides

    # Relationships
    client = relationship('Client', back_populates='standup_config')

    def __repr__(self):
        return f"<StandupConfig(id={self.id}, client_id={self.client_id}, schedule_type='{self.schedule_type}', time={self.schedule_time})>"

    @property
    def is_active(self) -> bool:
        """Check if this standup config is active"""
        return not self.is_paused and self.client.is_active
