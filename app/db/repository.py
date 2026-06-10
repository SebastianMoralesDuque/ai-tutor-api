"""
Repository layer — all database access goes through here.

Services never touch SQLAlchemy models directly. This keeps the
data access pattern testable and swappable.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    User, Concept, UserConcept, Mistake, LearningSession,
    QuizQuestionDB, TopicProgress, UserMemory,
)


# ── User ──────────────────────────────────────────────────────────────

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def update(self, user_id: str, **fields) -> Optional[User]:
        user = self.get(user_id)
        if not user:
            return None
        for k, v in fields.items():
            setattr(user, k, v)
        self.db.commit()
        self.db.refresh(user)
        return user


# ── Concept ───────────────────────────────────────────────────────────

class ConceptRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, name: str) -> Concept:
        concept = self.db.query(Concept).filter(Concept.name == name).first()
        if not concept:
            concept = Concept(name=name)
            self.db.add(concept)
            self.db.commit()
            self.db.refresh(concept)
        return concept

    def get(self, concept_id: str) -> Optional[Concept]:
        return self.db.query(Concept).filter(Concept.id == concept_id).first()


# ── UserConcept (mastery) ─────────────────────────────────────────────

class UserConceptRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, user_id: str, concept_id: str) -> UserConcept:
        uc = (
            self.db.query(UserConcept)
            .filter(UserConcept.user_id == user_id, UserConcept.concept_id == concept_id)
            .first()
        )
        if not uc:
            uc = UserConcept(user_id=user_id, concept_id=concept_id, mastery_level=0.0)
            self.db.add(uc)
            self.db.commit()
            self.db.refresh(uc)
        return uc

    def update_mastery(self, user_id: str, concept_id: str, delta: float) -> UserConcept:
        uc = self.get_or_create(user_id, concept_id)
        uc.mastery_level = max(0.0, min(100.0, uc.mastery_level + delta))
        uc.last_reviewed = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(uc)
        return uc

    def increment_session(self, user_id: str, concept_id: str) -> UserConcept:
        """Increment days studied for this concept."""
        uc = self.get_or_create(user_id, concept_id)
        uc.sessions_done = min(3, uc.sessions_done + 1)
        if uc.sessions_done >= 3 and uc.mastery_level >= 50:
            uc.completed = True
        self.db.commit()
        self.db.refresh(uc)
        return uc

    def schedule_review(self, user_id: str, concept_id: str, next_review: datetime) -> None:
        uc = self.get_or_create(user_id, concept_id)
        uc.next_review = next_review
        self.db.commit()

    def get_due_reviews(self, user_id: str, limit: int = 5) -> list[UserConcept]:
        now = datetime.now(timezone.utc)
        return (
            self.db.query(UserConcept)
            .filter(
                UserConcept.user_id == user_id,
                UserConcept.next_review <= now,
                UserConcept.completed == False,
            )
            .order_by(UserConcept.next_review.asc())
            .limit(limit)
            .all()
        )

    def get_weakest(self, user_id: str, limit: int = 5) -> list[UserConcept]:
        return (
            self.db.query(UserConcept)
            .filter(UserConcept.user_id == user_id, UserConcept.completed == False)
            .order_by(UserConcept.mastery_level.asc())
            .limit(limit)
            .all()
        )

    def get_all_for_user(self, user_id: str) -> list[UserConcept]:
        return (
            self.db.query(UserConcept)
            .filter(UserConcept.user_id == user_id)
            .all()
        )

    def get_completed_count(self, user_id: str) -> int:
        return (
            self.db.query(func.count(UserConcept.id))
            .filter(UserConcept.user_id == user_id, UserConcept.completed == True)
            .scalar()
        )


# ── TopicProgress ─────────────────────────────────────────────────────

class TopicProgressRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, user_id: str, topic: str) -> TopicProgress:
        tp = (
            self.db.query(TopicProgress)
            .filter(TopicProgress.user_id == user_id, TopicProgress.topic == topic)
            .first()
        )
        if not tp:
            tp = TopicProgress(user_id=user_id, topic=topic)
            self.db.add(tp)
            self.db.commit()
            self.db.refresh(tp)
        return tp

    def get_current(self, user_id: str) -> Optional[TopicProgress]:
        return (
            self.db.query(TopicProgress)
            .filter(TopicProgress.user_id == user_id, TopicProgress.status == "in_progress")
            .first()
        )

    def complete_topic(self, user_id: str, topic: str) -> TopicProgress:
        tp = self.get_or_create(user_id, topic)
        tp.status = "completed"
        tp.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(tp)
        return tp

    def increment_concepts_completed(self, user_id: str, topic: str) -> TopicProgress:
        tp = self.get_or_create(user_id, topic)
        tp.concepts_completed = min(3, tp.concepts_completed + 1)
        self.db.commit()
        self.db.refresh(tp)
        return tp

    def get_completed_topics(self, user_id: str) -> list[TopicProgress]:
        return (
            self.db.query(TopicProgress)
            .filter(TopicProgress.user_id == user_id, TopicProgress.status == "completed")
            .order_by(TopicProgress.completed_at.desc())
            .all()
        )


# ── UserMemory ────────────────────────────────────────────────────────

class UserMemoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: str) -> Optional[UserMemory]:
        return self.db.query(UserMemory).filter(UserMemory.user_id == user_id).first()

    def get_or_create(self, user_id: str) -> UserMemory:
        mem = self.db.query(UserMemory).filter(UserMemory.user_id == user_id).first()
        if not mem:
            mem = UserMemory(user_id=user_id)
            self.db.add(mem)
            self.db.commit()
            self.db.refresh(mem)
        return mem

    def update(self, user_id: str, **fields) -> UserMemory:
        mem = self.get_or_create(user_id)
        for k, v in fields.items():
            if isinstance(v, list):
                setattr(mem, k, json.dumps(v, ensure_ascii=False))
            else:
                setattr(mem, k, v)
        mem.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(mem)
        return mem

    def add_interest(self, user_id: str, interest: str) -> UserMemory:
        mem = self.get_or_create(user_id)
        current = json.loads(mem.interests) if mem.interests else []
        if interest not in current:
            current.append(interest)
            mem.interests = json.dumps(current, ensure_ascii=False)
            mem.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(mem)
        return mem

    def add_weak_area(self, user_id: str, area: str) -> UserMemory:
        mem = self.get_or_create(user_id)
        current = json.loads(mem.weak_areas) if mem.weak_areas else []
        if area not in current:
            current.append(area)
            mem.weak_areas = json.dumps(current, ensure_ascii=False)
            mem.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(mem)
        return mem

    def add_topic_studied(self, user_id: str, topic: str) -> UserMemory:
        mem = self.get_or_create(user_id)
        current = json.loads(mem.topics_studied) if mem.topics_studied else []
        if topic not in current:
            current.append(topic)
            mem.topics_studied = json.dumps(current, ensure_ascii=False)
            mem.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(mem)
        return mem

    def get_context_dict(self, user_id: str) -> dict:
        """Build context dict for AI prompts."""
        mem = self.get(user_id)
        if not mem:
            return {}
        return {
            "interests": json.loads(mem.interests) if mem.interests else [],
            "weak_areas": json.loads(mem.weak_areas) if mem.weak_areas else [],
            "topics_studied": json.loads(mem.topics_studied) if mem.topics_studied else [],
            "learning_style": mem.learning_style or "",
            "notes": mem.notes or "",
        }


# ── Mistake ───────────────────────────────────────────────────────────

class MistakeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, mistake: Mistake) -> Mistake:
        self.db.add(mistake)
        self.db.commit()
        self.db.refresh(mistake)
        return mistake

    def get_recent(self, user_id: str, limit: int = 10) -> list[Mistake]:
        return (
            self.db.query(Mistake)
            .filter(Mistake.user_id == user_id)
            .order_by(Mistake.timestamp.desc())
            .limit(limit)
            .all()
        )

    def get_by_user_and_concept(self, user_id: str, concept_id: str) -> list[Mistake]:
        return (
            self.db.query(Mistake)
            .filter(Mistake.user_id == user_id, Mistake.concept_id == concept_id)
            .order_by(Mistake.timestamp.desc())
            .all()
        )


# ── LearningSession ───────────────────────────────────────────────────

class SessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, session: LearningSession) -> LearningSession:
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_today(self, user_id: str) -> Optional[LearningSession]:
        """Check if user already had a session today."""
        today = datetime.now(timezone.utc).date()
        return (
            self.db.query(LearningSession)
            .filter(
                LearningSession.user_id == user_id,
                func.date(LearningSession.date) == today,
            )
            .first()
        )

    def count_streak(self, user_id: str) -> int:
        sessions = (
            self.db.query(LearningSession.date)
            .filter(LearningSession.user_id == user_id)
            .order_by(LearningSession.date.desc())
            .all()
        )
        if not sessions:
            return 0

        streak = 0
        expected_date = datetime.now(timezone.utc).date()

        for (session_date,) in sessions:
            session_day = session_date.date() if session_date else None
            if session_day == expected_date:
                streak += 1
                expected_date -= timedelta(days=1)
            elif session_day == expected_date - timedelta(days=1):
                expected_date = session_day
                streak += 1
                expected_date -= timedelta(days=1)
            else:
                break

        return streak


# ── QuizQuestion ──────────────────────────────────────────────────────

class QuizQuestionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_many(self, questions: list[QuizQuestionDB]) -> list[QuizQuestionDB]:
        self.db.add_all(questions)
        self.db.commit()
        for q in questions:
            self.db.refresh(q)
        return questions

    def get(self, question_id: str) -> Optional[QuizQuestionDB]:
        return self.db.query(QuizQuestionDB).filter(QuizQuestionDB.id == question_id).first()

    def get_by_session(self, session_id: str) -> list[QuizQuestionDB]:
        return (
            self.db.query(QuizQuestionDB)
            .filter(QuizQuestionDB.session_id == session_id)
            .order_by(QuizQuestionDB.question_index.asc())
            .all()
        )

    def get_latest_for_user(self, user_id: str) -> list[QuizQuestionDB]:
        latest_session = (
            self.db.query(LearningSession)
            .filter(LearningSession.user_id == user_id)
            .order_by(LearningSession.date.desc())
            .first()
        )
        if not latest_session:
            return []
        return self.get_by_session(latest_session.id)
