"""Chat tutor endpoint."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.ai_client import get_ai_client
from app.core.config import limiter
from app.db.database import get_db
from app.schemas.progress import ChatRequest, ChatResponse
from app.services.tutor_service import TutorService

logger = logging.getLogger("ai-tutor.routes.chat")
router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat(request: Request, payload: ChatRequest, db: Session = Depends(get_db)):
    logger.info("Chat message from user=%s", payload.user_id)
    ai = get_ai_client()
    svc = TutorService(db, ai)
    try:
        response = await svc.chat(payload.user_id, payload.message)
        logger.info("Chat response sent to user=%s (length=%d)", payload.user_id, len(response))
    except ValueError as e:
        logger.warning("Chat failed for user=%s: %s", payload.user_id, e)
        raise HTTPException(status_code=404, detail=str(e))
    return ChatResponse(response=response)
