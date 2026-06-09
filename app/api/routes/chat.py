"""Chat tutor endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.ai_client import get_ai_client
from app.db.database import get_db
from app.schemas.progress import ChatRequest, ChatResponse
from app.services.tutor_service import TutorService

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    ai = get_ai_client()
    svc = TutorService(db, ai)
    try:
        response = svc.chat(payload.user_id, payload.message)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ChatResponse(response=response)
