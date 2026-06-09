"""
Learning service — orchestrates daily sessions and answer evaluation.

This is the brain: it decides what to teach and how to adapt.
"""

from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.core.ai_client import AIClient
from app.core.config import settings
from app.db.models import Mistake
from app.db.repository import (
    UserRepository,
    ConceptRepository,
    UserConceptRepository,
    MistakeRepository,
    SessionRepository,
)


class LearningService:
    def __init__(self, db: Session, ai: AIClient):
        self.users = UserRepository(db)
        self.concepts = ConceptRepository(db)
        self.user_concepts = UserConceptRepository(db)
        self.mistakes = MistakeRepository(db)
        self.sessions = SessionRepository(db)
        self.ai = ai
        self.db = db

    def generate_daily_session(self, user_id: str) -> dict:
        """
        Core loop:
        1. Load user profile
        2. Find weakest concepts + due reviews
        3. Fetch recent mistakes
        4. Generate lesson + quiz via AI
        5. Record session
        """
        user = self.users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        topic = user.topic or "general knowledge"

        # Determine what to focus on
        due_reviews = self.user_concepts.get_due_reviews(user_id, limit=3)
        weakest = self.user_concepts.get_weakest(user_id, limit=3)

        # Build concept list: due reviews first, then weakest, then topic-derived
        concept_names = []
        for uc in due_reviews + weakest:
            concept = self.concepts.get(uc.concept_id)
            if concept and concept.name not in concept_names:
                concept_names.append(concept.name)

        # Fallback: derive concepts from topic
        if not concept_names:
            concept_names = [f"{topic} fundamentals", f"{topic} practice", f"{topic} advanced"]

        # Fetch recent mistakes for context
        recent_mistakes_raw = self.mistakes.get_recent(user_id, limit=5)
        mistakes = [
            {
                "concept": self.concepts.get(m.concept_id).name if self.concepts.get(m.concept_id) else "unknown",
                "error_description": m.error_description,
            }
            for m in recent_mistakes_raw
        ]

        # Generate via AI
        lesson = self.ai.generate_lesson(topic, concept_names, mistakes, user.daily_time)
        quiz = self.ai.generate_quiz(topic, lesson, concept_names, mistakes)

        # Record the session
        from app.db.models import LearningSession
        session_record = LearningSession(
            user_id=user_id,
            topic=topic,
            concepts_covered=",".join(concept_names[:5]),
        )
        self.sessions.create(session_record)

        # Ensure all concepts exist in DB and link to user
        for name in concept_names:
            concept = self.concepts.get_or_create(name)
            self.user_concepts.get_or_create(user_id, concept.id)

        return {
            "lesson": lesson,
            "quiz": quiz,
        }

    def submit_answer(self, user_id: str, question_id: str, answer: str) -> dict:
        """
        Evaluate answer, update mastery, record mistakes.
        """
        user = self.users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Find the concept for this question
        all_uc = self.user_concepts.get_all_for_user(user_id)
        concept_name = "general"
        concept_id = None
        if all_uc:
            first_uc = all_uc[0]
            concept = self.concepts.get(first_uc.concept_id)
            if concept:
                concept_name = concept.name
                concept_id = concept.id

        # Evaluate via AI — pass question_id as context, answer to evaluate
        result = self.ai.evaluate_answer(
            question=f"Question ID: {question_id}",
            options=[],
            answer=answer,
        )
        correct = result.get("correct", False)
        feedback = result.get("feedback", "")

        # Update mastery
        delta = settings.MASTERY_INCREASE_ON_CORRECT if correct else settings.MASTERY_DECREASE_ON_WRONG
        if concept_id:
            self.user_concepts.update_mastery(user_id, concept_id, delta)

            # Spaced repetition: schedule next review
            if correct:
                # Increase interval based on mastery
                uc = self.user_concepts.get_or_create(user_id, concept_id)
                hours = settings.REVIEW_INTERVAL_BASE_HOURS * (1 + uc.mastery_level / 50)
            else:
                # Review again soon
                hours = 1

            next_review = datetime.now(timezone.utc) + timedelta(hours=hours)
            self.user_concepts.schedule_review(user_id, concept_id, next_review)

        # Record mistake if wrong
        if not correct and concept_id:
            mistake = Mistake(
                user_id=user_id,
                concept_id=concept_id,
                error_description=feedback,
                question_text=question_id,
                user_answer=answer,
            )
            self.mistakes.create(mistake)

        # Build updated progress
        updated = {
            "concept": concept_name,
            "mastery_level": (
                self.user_concepts.get_or_create(user_id, concept_id).mastery_level
                if concept_id else 0
            ),
            "correct": correct,
        }

        return {
            "correct": correct,
            "feedback": feedback,
            "concept": concept_name,
            "mastery_delta": delta,
            "updated_progress": updated,
        }
