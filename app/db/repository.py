"""
Repository layer — all database access goes through here.

Services never touch SQLAlchemy models directly. This keeps the
data access pattern testable and swappable (e.g., switch to asyncpg later).
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import User, Concept, UserConcept, Mistake, LearningSession


# ── User ─────────────────────────────────────────────────────────────

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


# ── Concept ──────────────────────────────────────────────────────────

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


# ── UserConcept (mastery) ────────────────────────────────────────────

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
        """Adjust mastery by delta, clamped to [0, 100]."""
        uc = self.get_or_create(user_id, concept_id)
        uc.mastery_level = max(0.0, min(100.0, uc.mastery_level + delta))
        uc.last_reviewed = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(uc)
        return uc

    def schedule_review(self, user_id: str, concept_id: str, next_review: datetime) -> None:
        uc = self.get_or_create(user_id, concept_id)
        uc.next_review = next_review
        self.db.commit()

    def get_due_reviews(self, user_id: str, limit: int = 5) -> list[UserConcept]:
        """Concepts due for spaced repetition review."""
        now = datetime.now(timezone.utc)
        return (
            self.db.query(UserConcept)
            .filter(
                UserConcept.user_id == user_id,
                UserConcept.next_review <= now,
            )
            .order_by(UserConcept.next_review.asc())
            .limit(limit)
            .all()
        )

    def get_weakest(self, user_id: str, limit: int = 5) -> list[UserConcept]:
        """Concepts with lowest mastery — need the most attention."""
        return (
            self.db.query(UserConcept)
            .filter(UserConcept.user_id == user_id)
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


# ── Mistake ──────────────────────────────────────────────────────────

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


# ── LearningSession ──────────────────────────────────────────────────

class SessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, session: LearningSession) -> LearningSession:
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def count_streak(self, user_id: str) -> int:
        """
        Count consecutive days with at least one learning session.
        Walks backwards from today.
        """
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
                # Allow today to not have a session yet (streak continues)
                expected_date = session_day
                streak += 1
                expected_date -= timedelta(days=1)
            else:
                break

        return streak
