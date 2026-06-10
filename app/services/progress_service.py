"""
Progress service — aggregates mastery, streaks, cycle state, and mistake history.
"""

import json
from sqlalchemy.orm import Session

from app.db.repository import (
    UserRepository,
    ConceptRepository,
    UserConceptRepository,
    MistakeRepository,
    SessionRepository,
    TopicProgressRepository,
    UserMemoryRepository,
)


class ProgressService:
    def __init__(self, db: Session):
        self.users = UserRepository(db)
        self.concepts = ConceptRepository(db)
        self.user_concepts = UserConceptRepository(db)
        self.mistakes = MistakeRepository(db)
        self.sessions = SessionRepository(db)
        self.topics = TopicProgressRepository(db)
        self.memory = UserMemoryRepository(db)

    def get_progress(self, user_id: str) -> dict:
        user = self.users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        topic = user.current_topic
        concept_names = [
            f"{topic} fundamentals",
            f"{topic} practice",
            f"{topic} advanced",
        ] if topic else []

        # Mastery per concept for current topic
        concept_mastery = []
        for i, name in enumerate(concept_names):
            concept = self.concepts.get_or_create(name)
            uc = self.user_concepts.get_or_create(user_id, concept.id)
            concept_mastery.append({
                "concept": name,
                "level": round(uc.mastery_level, 1),
                "sessions_done": uc.sessions_done,
                "completed": uc.completed,
                "is_current": i == user.current_concept_index,
            })

        # Completed topics
        completed_topics = self.topics.get_completed_topics(user_id)
        completed_list = [
            {"topic": tp.topic, "completed_at": tp.completed_at.isoformat() if tp.completed_at else None}
            for tp in completed_topics
        ]

        # Recent mistakes
        recent = self.mistakes.get_recent(user_id, limit=5)
        recent_mistakes = []
        for m in recent:
            concept = self.concepts.get(m.concept_id)
            recent_mistakes.append({
                "concept": concept.name if concept else "unknown",
                "error_description": m.error_description,
                "question_text": m.question_text,
                "user_answer": m.user_answer,
                "timestamp": m.timestamp.isoformat() if m.timestamp else "",
            })

        # Streak
        streak = self.sessions.count_streak(user_id)

        # Topic progress
        topic_progress = None
        if topic:
            tp = self.topics.get_current(user_id)
            if tp:
                topic_progress = {
                    "topic": tp.topic,
                    "status": tp.status,
                    "concepts_completed": tp.concepts_completed,
                    "started_at": tp.started_at.isoformat() if tp.started_at else None,
                }

        return {
            "user_id": user_id,
            "current_topic": topic,
            "streak": streak,
            "cycle": {
                "concept_index": user.current_concept_index,
                "day_in_cycle": user.concept_day,
                "total_concepts": 3,
                "days_per_concept": 3,
            },
            "topic_progress": topic_progress,
            "concept_mastery": concept_mastery,
            "completed_topics": completed_list,
            "recent_mistakes": recent_mistakes,
        }
