"""
Learning service — orchestrates daily sessions with 3-day cycle per concept.

Cycle logic:
  concept_index 0, day 1-3 → fundamentals
  concept_index 1, day 1-3 → practice
  concept_index 2, day 1-3 → advanced
  all 3 done → topic completed → suggest new topic

Each day: generate lesson + quiz for the CURRENT concept only.
"""

import json
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.core.ai_client import AIClient
from app.core.config import settings
from app.db.models import Mistake, QuizQuestionDB
from app.db.repository import (
    UserRepository,
    ConceptRepository,
    UserConceptRepository,
    MistakeRepository,
    SessionRepository,
    QuizQuestionRepository,
    TopicProgressRepository,
    UserMemoryRepository,
)


class LearningService:
    def __init__(self, db: Session, ai: AIClient):
        self.users = UserRepository(db)
        self.concepts = ConceptRepository(db)
        self.user_concepts = UserConceptRepository(db)
        self.mistakes = MistakeRepository(db)
        self.sessions = SessionRepository(db)
        self.quiz_questions = QuizQuestionRepository(db)
        self.topics = TopicProgressRepository(db)
        self.memory = UserMemoryRepository(db)
        self.ai = ai
        self.db = db

    # ── Concepts per topic ────────────────────────────────────────────
    # Fixed: every topic gets fundamentals → practice → advanced
    def _get_topic_concepts(self, topic: str) -> list[str]:
        return [
            f"{topic} fundamentals",
            f"{topic} practice",
            f"{topic} advanced",
        ]

    async def generate_daily_session(self, user_id: str) -> dict:
        """
        Core loop with 3-day cycle:
        1. Load user + determine current concept + day
        2. If first visit to this concept, initialize it
        3. Generate lesson + quiz focused on current concept
        4. Record session + advance cycle
        """
        user = self.users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        topic = user.current_topic
        if not topic:
            raise ValueError("No topic set. Call /api/users/ to set a topic first.")

        # ── Determine current concept ──
        concept_names = self._get_topic_concepts(topic)
        concept_index = user.current_concept_index
        concept_day = user.concept_day
        current_concept = concept_names[concept_index]

        # ── Initialize concept start date if needed ──
        if not user.concept_start_date:
            self.users.update(user_id, concept_start_date=datetime.now(timezone.utc))

        # ── Ensure topic progress exists ──
        topic_progress = self.topics.get_or_create(user_id, topic)

        # ── Ensure concept exists in DB ──
        concept = self.concepts.get_or_create(current_concept)
        user_concept = self.user_concepts.get_or_create(user_id, concept.id)

        # ── Fetch recent mistakes for this concept ──
        recent_mistakes_raw = self.mistakes.get_recent(user_id, limit=5)
        mistakes = [
            {
                "concept": self.concepts.get(m.concept_id).name if self.concepts.get(m.concept_id) else "unknown",
                "error_description": m.error_description,
            }
            for m in recent_mistakes_raw
            if self.concepts.get(m.concept_id) and self.concepts.get(m.concept_id).name == current_concept
        ]

        # ── Generate lesson (focused on current concept) ──
        lesson = await self.ai.generate_lesson(
            topic=topic,
            concepts=[current_concept],
            mistakes=mistakes,
            daily_time=user.daily_time,
            day_in_cycle=concept_day,
            concept_type=concept_names[concept_index].split()[-1],  # fundamentals/practice/advanced
        )

        # ── Generate quiz (3 questions about this concept) ──
        import logging
        _log = logging.getLogger("ai-tutor.quiz")
        quiz = await self.ai.generate_quiz(
            topic=topic,
            lesson=lesson,
            concepts=[current_concept],
            mistakes=mistakes,
        )
        _log.info("Quiz RAW from AI: %d questions", len(quiz))
        for i, q in enumerate(quiz):
            _log.info("  [%d] correct_answer_index=%s type=%s options=%d",
                      i, q.get("correct_answer_index"), type(q.get("correct_answer_index")).__name__, len(q.get("options", [])))

        # ── Validate correctAnswerIndex for each question (safety net) ──
        pre_filter = len(quiz)
        quiz = [
            q for q in quiz
            if isinstance(q.get("correct_answer_index"), int) and 0 <= q["correct_answer_index"] <= 3
        ]
        _log.info("Quiz after filter: %d (was %d)", len(quiz), pre_filter)

        # ── Record learning session ──
        from app.db.models import LearningSession
        session_record = LearningSession(
            user_id=user_id,
            topic=topic,
            concept_name=current_concept,
            day_in_cycle=concept_day,
            concepts_covered=current_concept,
        )
        self.sessions.create(session_record)

        # ── Persist quiz questions ──
        db_questions = []
        for i, q in enumerate(quiz):
            db_q = QuizQuestionDB(
                session_id=session_record.id,
                user_id=user_id,
                question_index=i,
                question=q.get("question", ""),
                options=json.dumps(q.get("options", []), ensure_ascii=False),
                correct_answer_index=q.get("correct_answer_index", -1),
                concept=current_concept,
            )
            db_questions.append(db_q)
        _log.info("Persisting %d quiz questions for session %s", len(db_questions), session_record.id[:12])
        self.quiz_questions.create_many(db_questions)
        _log.info("Quiz questions persisted OK")

        # ── Advance cycle ──
        self._advance_cycle(user_id, user, concept_index, concept_day, topic)

        return {
            "lesson": lesson,
            "quiz": quiz,
            "cycle_info": {
                "topic": topic,
                "concept": current_concept,
                "concept_index": concept_index,
                "day_in_cycle": concept_day,
                "total_concepts": 3,
                "topic_completed": False,  # will be True if this was the last day
            },
        }

    def _advance_cycle(
        self, user_id: str, user, concept_index: int, concept_day: int, topic: str
    ):
        """Advance the learning cycle after a session."""
        concept_names = self._get_topic_concepts(topic)

        if concept_day < 3:
            # Same concept, next day
            self.users.update(user_id, concept_day=concept_day + 1)
        elif concept_index < 2:
            # Next concept, day 1
            # Mark current concept as completed
            old_concept = self.concepts.get_or_create(concept_names[concept_index])
            self.user_concepts.increment_session(user_id, old_concept.id)

            # Move to next concept
            self.users.update(
                user_id,
                current_concept_index=concept_index + 1,
                concept_day=1,
                concept_start_date=datetime.now(timezone.utc),
            )
            # Update topic progress
            self.topics.increment_concepts_completed(user_id, topic)
        else:
            # Topic completed! All 3 concepts × 3 days = 9 days done
            old_concept = self.concepts.get_or_create(concept_names[concept_index])
            self.user_concepts.increment_session(user_id, old_concept.id)
            self.topics.increment_concepts_completed(user_id, topic)
            self.topics.complete_topic(user_id, topic)

            # Update user memory
            self.memory.add_topic_studied(user_id, topic)

            # Reset user for next topic (user needs to pick a new one)
            self.users.update(
                user_id,
                current_topic="",
                current_concept_index=0,
                concept_day=1,
                concept_start_date=None,
            )

    async def submit_answer(self, user_id: str, question_id: str, answer: str) -> dict:
        """
        Evaluate answer by looking up the question in DB.
        No AI for basic correct/incorrect — just compare indices.
        AI only for feedback on wrong answers.
        """
        user = self.users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Look up the question in DB
        db_question = self.quiz_questions.get(question_id)
        if not db_question:
            return {
                "correct": False,
                "feedback": "Pregunta no encontrada. Intenta generar una nueva sesión.",
                "concept": "general",
                "mastery_delta": 0.0,
                "updated_progress": {},
            }

        # Parse options and correct answer
        try:
            options = json.loads(db_question.options)
        except (json.JSONDecodeError, TypeError):
            options = []

        correct_index = db_question.correct_answer_index
        concept_name = db_question.concept or "general"

        # Find concept in DB
        concept = self.concepts.get_or_create(concept_name)
        concept_id = concept.id

        # Determine if correct
        user_index = self._parse_answer_index(answer, len(options))
        correct = user_index == correct_index

        # Update mastery
        delta = settings.MASTERY_INCREASE_ON_CORRECT if correct else settings.MASTERY_DECREASE_ON_WRONG
        self.user_concepts.update_mastery(user_id, concept_id, delta)

        # Spaced repetition
        if correct:
            uc = self.user_concepts.get_or_create(user_id, concept_id)
            hours = settings.REVIEW_INTERVAL_BASE_HOURS * (1 + uc.mastery_level / 50)
        else:
            hours = 1

        next_review = datetime.now(timezone.utc) + timedelta(hours=hours)
        self.user_concepts.schedule_review(user_id, concept_id, next_review)

        # Generate feedback
        if correct:
            feedback = "¡Correcto! Bien hecho."
        else:
            correct_option = options[correct_index] if correct_index < len(options) else "la respuesta correcta"
            result = await self.ai.evaluate_answer(
                question=db_question.question,
                options=options,
                answer=answer,
            )
            feedback = result.get("feedback", f"La respuesta correcta es: {correct_option}")

        # Record mistake if wrong
        if not correct:
            mistake = Mistake(
                user_id=user_id,
                concept_id=concept_id,
                error_description=feedback,
                question_text=db_question.question,
                user_answer=answer,
            )
            self.mistakes.create(mistake)
            # Update user memory with weak area
            self.memory.add_weak_area(user_id, concept_name)

        # Build updated progress
        uc = self.user_concepts.get_or_create(user_id, concept_id)
        updated = {
            "concept": concept_name,
            "mastery_level": uc.mastery_level,
            "correct": correct,
        }

        return {
            "correct": correct,
            "feedback": feedback,
            "concept": concept_name,
            "mastery_delta": delta,
            "updated_progress": updated,
        }

    def _parse_answer_index(self, answer: str, num_options: int) -> int:
        """Parse user answer into an index (0-3)."""
        answer = answer.strip().lower()

        if answer.isdigit():
            idx = int(answer)
            if 0 <= idx < num_options:
                return idx

        letter_map = {"a": 0, "b": 1, "c": 2, "d": 3}
        if answer in letter_map:
            idx = letter_map[answer]
            if idx < num_options:
                return idx

        return -1
