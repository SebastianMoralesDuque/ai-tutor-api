"""User management endpoints."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import limiter
from app.db.database import get_db
from app.db.models import User
from app.db.repository import UserRepository, TopicProgressRepository, UserMemoryRepository
from app.schemas.user import UserCreate, UserUpdate, UserResponse

logger = logging.getLogger("ai-tutor.routes.user")
router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/", status_code=201, response_model=UserResponse)
@limiter.limit("30/minute")
def create_user(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    logger.info("Creating user: topic=%s daily_time=%d", payload.topic, payload.daily_time)

    repo = UserRepository(db)
    user = User(
        current_topic=payload.topic,
        daily_time=payload.daily_time,
        current_concept_index=0,
        concept_day=1,
        concept_start_date=datetime.now(timezone.utc),
    )
    created = repo.create(user)

    # Create topic progress
    if payload.topic:
        topics_repo = TopicProgressRepository(db)
        topics_repo.get_or_create(created.id, payload.topic)

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


@router.get("/{user_id}", response_model=UserResponse)
@limiter.limit("30/minute")
def get_user(request: Request, user_id: str, db: Session = Depends(get_db)):
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


@router.patch("/{user_id}", response_model=UserResponse)
@limiter.limit("30/minute")
def update_user(request: Request, user_id: str, payload: UserUpdate, db: Session = Depends(get_db)):
    repo = UserRepository(db)

    # Build update dict from non-None fields
    fields = {}
    if payload.current_topic is not None:
        fields["current_topic"] = payload.current_topic
    if payload.daily_time is not None:
        fields["daily_time"] = payload.daily_time

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
