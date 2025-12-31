"""Standup response model"""

from sqlalchemy import Column, Integer, String, ForeignKey, Date, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from src.models.base import Base


class StandupResponse(Base):
    """
    Client's standup response data

    Stores answers to daily standup questions
    """

    __tablename__ = 'standup_responses'

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id', ondelete='CASCADE'), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False, index=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    scheduled_date = Column(Date, nullable=False)  # Date this standup was for
    accomplishments = Column(Text, nullable=True)
    working_on = Column(Text, nullable=True)
    blockers = Column(Text, nullable=True)
    response_time_seconds = Column(Integer, nullable=True)  # Time taken to complete
    message_ts = Column(String(20), nullable=True)  # Slack message timestamp

    # Relationships
    client = relationship('Client', back_populates='standup_responses')
    workspace = relationship('Workspace', back_populates='standup_responses')

    def __repr__(self):
        return f"<StandupResponse(id={self.id}, client_id={self.client_id}, date={self.scheduled_date})>"

    @property
    def has_blockers(self) -> bool:
        """Check if blockers were reported"""
        return bool(self.blockers and self.blockers.strip())
