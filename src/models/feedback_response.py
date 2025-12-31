"""Feedback response model"""

from sqlalchemy import Column, Integer, String, ForeignKey, Date, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from src.models.base import Base


class FeedbackResponse(Base):
    """
    Client's weekly feedback response

    Stores answers to Friday feedback questions including ratings
    """

    __tablename__ = 'feedback_responses'

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id', ondelete='CASCADE'), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False, index=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    week_ending = Column(Date, nullable=False)  # Friday date this feedback is for
    feeling_rating = Column(Integer, nullable=True)  # 1-5 scale
    feeling_text = Column(Text, nullable=True)  # Additional thoughts
    improvements = Column(Text, nullable=True)
    blockers = Column(Text, nullable=True)
    satisfaction_rating = Column(Integer, nullable=True)  # 1-5 scale
    response_time_seconds = Column(Integer, nullable=True)
    message_ts = Column(String(20), nullable=True)  # Original DM message timestamp
    vibe_channel_message_ts = Column(String(20), nullable=True)  # Posted feedback message timestamp

    # Relationships
    client = relationship('Client', back_populates='feedback_responses')
    workspace = relationship('Workspace', back_populates='feedback_responses')

    def __repr__(self):
        return f"<FeedbackResponse(id={self.id}, client_id={self.client_id}, week={self.week_ending})>"

    @property
    def has_concerns(self) -> bool:
        """Check if concerns/blockers were reported"""
        return bool(self.blockers and self.blockers.strip())

    @property
    def is_positive(self) -> bool:
        """Check if overall feedback is positive (4-5 ratings)"""
        return (
            (self.feeling_rating and self.feeling_rating >= 4) and
            (self.satisfaction_rating and self.satisfaction_rating >= 4)
        )

    @property
    def needs_attention(self) -> bool:
        """Check if feedback indicates issues (1-2 ratings)"""
        return (
            (self.feeling_rating and self.feeling_rating <= 2) or
            (self.satisfaction_rating and self.satisfaction_rating <= 2) or
            self.has_concerns
        )
