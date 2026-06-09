"""
SQLAlchemy ORM models.

Flat relational design: User -> UserConcept -> Concept, User -> Mistake -> Concept.
No deep inheritance, no polymorphism — just tables and foreign keys.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey, Text, Index
)
from sqlalchemy.orm import relationship

from app.db.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id = Column(String(32), primary_key=True, default=_uuid)
    topic = Column(String(255), nullable=False, default="")
    daily_time = Column(Integer, nullable=False, default=20)  # minutes
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    concepts = relationship("UserConcept", back_populates="user", cascade="all, delete-orphan")
    mistakes = relationship("Mistake", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("LearningSession", back_populates="user", cascade="all, delete-orphan")


class Concept(Base):
    __tablename__ = "concepts"

    id = Column(String(32), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False, unique=True)

    user_concepts = relationship("UserConcept", back_populates="concept")
    mistakes = relationship("Mistake", back_populates="concept")


class UserConcept(Base):
    """Per-user mastery tracking for each concept."""
    __tablename__ = "user_concepts"
    __table_args__ = (
        Index("ix_user_concepts_user_concept", "user_id", "concept_id", unique=True),
    )

    id = Column(String(32), primary_key=True, default=_uuid)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False)
    concept_id = Column(String(32), ForeignKey("concepts.id"), nullable=False)
    mastery_level = Column(Float, nullable=False, default=0.0)  # 0–100
    last_reviewed = Column(DateTime, nullable=True)
    next_review = Column(DateTime, nullable=True)  # spaced repetition schedule

    user = relationship("User", back_populates="concepts")
    concept = relationship("Concept", back_populates="user_concepts")


class Mistake(Base):
    __tablename__ = "mistakes"
    __table_args__ = (
        Index("ix_mistakes_user_concept", "user_id", "concept_id"),
    )

    id = Column(String(32), primary_key=True, default=_uuid)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False)
    concept_id = Column(String(32), ForeignKey("concepts.id"), nullable=False)
    error_description = Column(Text, nullable=False, default="")
    question_text = Column(Text, nullable=False, default="")
    user_answer = Column(Text, nullable=False, default="")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="mistakes")
    concept = relationship("Concept", back_populates="mistakes")


class LearningSession(Base):
    """Record of each daily session for streak tracking."""
    __tablename__ = "learning_sessions"

    id = Column(String(32), primary_key=True, default=_uuid)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False)
    topic = Column(String(255), nullable=False)
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    concepts_covered = Column(Text, nullable=False, default="")  # comma-separated concept IDs

    user = relationship("User", back_populates="sessions")
