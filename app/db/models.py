"""
SQLAlchemy ORM models.

Cycle-based learning design:
  User → has current topic + concept index + day in cycle
  TopicProgress → tracks each topic lifecycle (in_progress / completed)
  UserConcept → mastery per concept per user
  Mistake → what went wrong
  LearningSession → one per day visited
  QuizQuestionDB → persisted quiz for submit-answer validation
  UserMemory → tutor's long-term memory about the user
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey, Text, Index, Boolean
)
from sqlalchemy.orm import relationship

from app.db.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


# ── User ──────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String(32), primary_key=True, default=_uuid)
    daily_time = Column(Integer, nullable=False, default=20)  # minutes
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # ── Cycle state ──
    current_topic = Column(String(255), nullable=False, default="")
    current_concept_index = Column(Integer, nullable=False, default=0)  # 0, 1, 2
    concept_day = Column(Integer, nullable=False, default=1)  # 1, 2, 3
    concept_start_date = Column(DateTime, nullable=True)

    # ── Relationships ──
    concepts = relationship("UserConcept", back_populates="user", cascade="all, delete-orphan")
    mistakes = relationship("Mistake", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("LearningSession", back_populates="user", cascade="all, delete-orphan")
    quiz_questions = relationship("QuizQuestionDB", backref="user", cascade="all, delete-orphan")
    topic_progress = relationship("TopicProgress", back_populates="user", cascade="all, delete-orphan")
    memory = relationship("UserMemory", back_populates="user", uselist=False, cascade="all, delete-orphan")


# ── Concept ───────────────────────────────────────────────────────────

class Concept(Base):
    __tablename__ = "concepts"

    id = Column(String(32), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False, unique=True)

    user_concepts = relationship("UserConcept", back_populates="concept")
    mistakes = relationship("Mistake", back_populates="concept")


# ── UserConcept (mastery per concept) ─────────────────────────────────

class UserConcept(Base):
    __tablename__ = "user_concepts"
    __table_args__ = (
        Index("ix_user_concepts_user_concept", "user_id", "concept_id", unique=True),
    )

    id = Column(String(32), primary_key=True, default=_uuid)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False)
    concept_id = Column(String(32), ForeignKey("concepts.id"), nullable=False)
    mastery_level = Column(Float, nullable=False, default=0.0)  # 0–100
    sessions_done = Column(Integer, nullable=False, default=0)  # days studied (0-3)
    completed = Column(Boolean, nullable=False, default=False)
    last_reviewed = Column(DateTime, nullable=True)
    next_review = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="concepts")
    concept = relationship("Concept", back_populates="user_concepts")


# ── TopicProgress (tracks full topic lifecycle) ───────────────────────

class TopicProgress(Base):
    __tablename__ = "topic_progress"
    __table_args__ = (
        Index("ix_topic_progress_user_topic", "user_id", "topic", unique=True),
    )

    id = Column(String(32), primary_key=True, default=_uuid)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False)
    topic = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="in_progress")  # in_progress | completed
    concepts_completed = Column(Integer, nullable=False, default=0)  # 0-3
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="topic_progress")


# ── UserMemory (tutor's long-term memory about the user) ─────────────

class UserMemory(Base):
    """
    The tutor remembers: interests, learning patterns, weak areas,
    topics studied, preferences. Updated after each meaningful interaction.
    """
    __tablename__ = "user_memory"

    id = Column(String(32), primary_key=True, default=_uuid)
    user_id = Column(String(32), ForeignKey("users.id"), unique=True, nullable=False)

    # ── What the tutor knows ──
    interests = Column(Text, nullable=False, default="[]")          # JSON array
    weak_areas = Column(Text, nullable=False, default="[]")         # JSON array
    topics_studied = Column(Text, nullable=False, default="[]")     # JSON array
    learning_style = Column(Text, nullable=False, default="")       # free text
    notes = Column(Text, nullable=False, default="")                # free text
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="memory")


# ── Mistake ───────────────────────────────────────────────────────────

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


# ── LearningSession ───────────────────────────────────────────────────

class LearningSession(Base):
    """Record of each daily session for streak tracking."""
    __tablename__ = "learning_sessions"

    id = Column(String(32), primary_key=True, default=_uuid)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False)
    topic = Column(String(255), nullable=False)
    concept_name = Column(String(255), nullable=False, default="")  # which concept was studied
    day_in_cycle = Column(Integer, nullable=False, default=1)       # 1, 2, or 3
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    concepts_covered = Column(Text, nullable=False, default="")

    user = relationship("User", back_populates="sessions")


# ── QuizQuestionDB ────────────────────────────────────────────────────

class QuizQuestionDB(Base):
    """Persisted quiz question — enables submit-answer validation without AI."""
    __tablename__ = "quiz_questions"
    __table_args__ = (
        Index("ix_quiz_questions_session", "session_id"),
    )

    id = Column(String(32), primary_key=True, default=_uuid)
    session_id = Column(String(32), ForeignKey("learning_sessions.id"), nullable=False)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False)
    question_index = Column(Integer, nullable=False, default=0)
    question = Column(Text, nullable=False)
    options = Column(Text, nullable=False)  # JSON array of 4 strings
    correct_answer_index = Column(Integer, nullable=False, default=0)
    concept = Column(String(255), nullable=False, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
