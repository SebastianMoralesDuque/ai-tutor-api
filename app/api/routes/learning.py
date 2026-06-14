"""Learning session and answer evaluation endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.ai_client import get_ai_client
from app.core.config import limiter
from app.db.database import get_db
from app.schemas.learning import (
    DailySessionRequest,
    DailySessionResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.schemas.progress import ProgressResponse
from app.services.learning_service import LearningService
from app.services.progress_service import ProgressService

logger = logging.getLogger("ai-tutor.routes.learning")
router = APIRouter(prefix="/api", tags=["learning"])


@router.post("/daily-session", response_model=DailySessionResponse)
@limiter.limit("30/minute")
async def daily_session(request: Request, payload: DailySessionRequest, db: Session = Depends(get_db)):
    logger.info("Daily session requested for user=%s", payload.user_id)
    ai = get_ai_client()
    svc = LearningService(db, ai)
    try:
        result = await svc.generate_daily_session(payload.user_id)
        logger.info("Daily session generated for user=%s concept=%s", payload.user_id, result.get("cycle_info", {}).get("concept", ""))
    except ValueError as e:
        logger.warning("Daily session failed for user=%s: %s", payload.user_id, e)
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.post("/submit-answer", response_model=SubmitAnswerResponse)
@limiter.limit("30/minute")
async def submit_answer(request: Request, payload: SubmitAnswerRequest, db: Session = Depends(get_db)):
    logger.info("Answer submitted: user=%s question=%s", payload.user_id, payload.question_id)
    ai = get_ai_client()
    svc = LearningService(db, ai)
    try:
        result = await svc.submit_answer(payload.user_id, payload.question_id, payload.answer)
        logger.info("Answer evaluated: user=%s correct=%s", payload.user_id, result.get("correct"))
    except ValueError as e:
        logger.warning("Submit answer failed for user=%s: %s", payload.user_id, e)
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.get("/progress/{user_id}", response_model=ProgressResponse)
@limiter.limit("30/minute")
async def get_progress(request: Request, user_id: str, db: Session = Depends(get_db)):
    logger.info("Progress requested for user=%s", user_id)
    svc = ProgressService(db)
    try:
        return svc.get_progress(user_id)
    except ValueError as e:
        logger.warning("Progress failed for user=%s: %s", user_id, e)
        raise HTTPException(status_code=404, detail=str(e))
