"""
Tutor service — free-form chat with persistent memory context.
The tutor learns about the user over time.
"""

import json
from sqlalchemy.orm import Session

from app.core.ai_client import AIClient
from app.db.repository import (
    UserRepository,
    ConceptRepository,
    UserConceptRepository,
    MistakeRepository,
    UserMemoryRepository,
    SessionRepository,
)


class TutorService:
    def __init__(self, db: Session, ai: AIClient):
        self.users = UserRepository(db)
        self.concepts = ConceptRepository(db)
        self.user_concepts = UserConceptRepository(db)
        self.mistakes = MistakeRepository(db)
        self.memory = UserMemoryRepository(db)
        self.sessions = SessionRepository(db)
        self.ai = ai

    async def chat(self, user_id: str, message: str) -> str:
        """
        Send a message to the tutor with full student memory.
        """
        user = self.users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Build context from user's learning history
        all_uc = self.user_concepts.get_all_for_user(user_id)
        weak = []
        for uc in all_uc:
            if uc.mastery_level < 40 and not uc.completed:
                concept = self.concepts.get(uc.concept_id)
                if concept:
                    weak.append(concept.name)

        recent_mistakes_raw = self.mistakes.get_recent(user_id, limit=3)
        mistakes = [
            {
                "concept": (
                    self.concepts.get(m.concept_id).name
                    if self.concepts.get(m.concept_id)
                    else "unknown"
                ),
                "error_description": m.error_description,
            }
            for m in recent_mistakes_raw
        ]

        # Get persistent memory
        mem_ctx = self.memory.get_context_dict(user_id)

        # Get streak
        streak = self.sessions.count_streak(user_id)

        context = {
            "topic": user.current_topic,
            "weak_concepts": weak,
            "recent_mistakes": mistakes,
            "streak": streak,
            "interests": mem_ctx.get("interests", []),
            "topics_studied": mem_ctx.get("topics_studied", []),
        }

        return await self.ai.chat(message, context)
