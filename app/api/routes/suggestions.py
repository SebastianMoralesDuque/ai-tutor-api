"""Study suggestions endpoint — smart recommendations based on user history."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.ai_client import get_ai_client
from app.core.prompt_builder import build_suggestions_prompt
from app.db.database import get_db
from app.db.repository import UserRepository, TopicProgressRepository, UserMemoryRepository

router = APIRouter(prefix="/api", tags=["suggestions"])


@router.post("/suggestions")
def get_suggestions(payload: dict, db: Session = Depends(get_db)):
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    user = UserRepository(db).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user memory
    memory_repo = UserMemoryRepository(db)
    user_memory = memory_repo.get_context_dict(user_id)

    # Get completed topics
    topics_repo = TopicProgressRepository(db)
    completed = topics_repo.get_completed_topics(user_id)
    topics_completed = [tp.topic for tp in completed]

    # Build smart prompt
    ai = get_ai_client()
    prompt = build_suggestions_prompt(user_memory, topics_completed)
    messages = [
        {"role": "system", "content": prompt["system"]},
        {"role": "user", "content": prompt["user"]},
    ]

    try:
        raw = ai._chat(messages, temperature=0.8) if hasattr(ai, '_chat') else "[]"
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start != -1 and end > start:
            suggestions = json.loads(cleaned[start:end + 1])
        else:
            suggestions = json.loads(cleaned)
        suggestions = [str(s) for s in suggestions[:3]]
    except Exception:
        suggestions = []

    # Fallback if AI fails
    if len(suggestions) < 3:
        defaults = ["Ética", "Lógica", "Epistemología"]
        # Filter out already studied topics
        defaults = [d for d in defaults if d not in topics_completed]
        suggestions = (suggestions + defaults)[:3]

    return suggestions
