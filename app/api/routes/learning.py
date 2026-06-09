"""Learning session and answer evaluation endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.ai_client import get_ai_client
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

router = APIRouter(prefix="/api", tags=["learning"])


@router.post("/daily-session", response_model=DailySessionResponse)
def daily_session(payload: DailySessionRequest, db: Session = Depends(get_db)):
    ai = get_ai_client()
    svc = LearningService(db, ai)
    try:
        result = svc.generate_daily_session(payload.user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.post("/submit-answer", response_model=SubmitAnswerResponse)
def submit_answer(payload: SubmitAnswerRequest, db: Session = Depends(get_db)):
    ai = get_ai_client()
    svc = LearningService(db, ai)
    try:
        result = svc.submit_answer(payload.user_id, payload.question_id, payload.answer)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.get("/progress/{user_id}", response_model=ProgressResponse)
def get_progress(user_id: str, db: Session = Depends(get_db)):
    svc = ProgressService(db)
    try:
        return svc.get_progress(user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
