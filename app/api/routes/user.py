"""User management endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.db.repository import UserRepository, TopicProgressRepository, UserMemoryRepository

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/", status_code=201)
def create_user(payload: dict, db: Session = Depends(get_db)):
    topic = payload.get("topic", "")
    daily_time = payload.get("daily_time", 20)

    repo = UserRepository(db)
    user = User(
        current_topic=topic,
        daily_time=daily_time,
        current_concept_index=0,
        concept_day=1,
        concept_start_date=datetime.now(timezone.utc),
    )
    created = repo.create(user)

    # Create topic progress
    if topic:
        topics_repo = TopicProgressRepository(db)
        topics_repo.get_or_create(created.id, topic)

    # Create user memory
    memory_repo = UserMemoryRepository(db)
    memory_repo.get_or_create(created.id)

    return {
        "id": created.id,
        "current_topic": created.current_topic,
        "daily_time": created.daily_time,
        "current_concept_index": created.current_concept_index,
        "concept_day": created.concept_day,
        "created_at": created.created_at.isoformat() if created.created_at else None,
    }


@router.get("/{user_id}")
def get_user(user_id: str, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user = repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "current_topic": user.current_topic,
        "daily_time": user.daily_time,
        "current_concept_index": user.current_concept_index,
        "concept_day": user.concept_day,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.patch("/{user_id}")
def update_user(user_id: str, payload: dict, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    fields = {k: v for k, v in payload.items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    # If setting a new topic, create topic progress
    if "current_topic" in fields and fields["current_topic"]:
        topics_repo = TopicProgressRepository(db)
        topics_repo.get_or_create(user_id, fields["current_topic"])

    user = repo.update(user_id, **fields)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "current_topic": user.current_topic,
        "daily_time": user.daily_time,
        "current_concept_index": user.current_concept_index,
        "concept_day": user.concept_day,
    }
