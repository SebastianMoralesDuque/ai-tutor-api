"""
Progress service — aggregates mastery, streaks, and mistake history.
"""

from sqlalchemy.orm import Session

from app.db.repository import (
    UserRepository,
    ConceptRepository,
    UserConceptRepository,
    MistakeRepository,
    SessionRepository,
)


class ProgressService:
    def __init__(self, db: Session):
        self.users = UserRepository(db)
        self.concepts = ConceptRepository(db)
        self.user_concepts = UserConceptRepository(db)
        self.mistakes = MistakeRepository(db)
        self.sessions = SessionRepository(db)

    def get_progress(self, user_id: str) -> dict:
        user = self.users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Mastery per concept
        all_uc = self.user_concepts.get_all_for_user(user_id)
        concept_mastery = []
        for uc in all_uc:
            concept = self.concepts.get(uc.concept_id)
            if concept:
                concept_mastery.append({
                    "concept": concept.name,
                    "level": round(uc.mastery_level, 1),
                    "last_reviewed": (
                        uc.last_reviewed.isoformat() if uc.last_reviewed else None
                    ),
                })

        # Sort by mastery ascending (weakest first)
        concept_mastery.sort(key=lambda x: x["level"])

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

        return {
            "user_id": user_id,
            "topic": user.topic,
            "streak": streak,
            "concept_mastery": concept_mastery,
            "recent_mistakes": recent_mistakes,
        }
