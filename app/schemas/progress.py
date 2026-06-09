"""Progress and chat schemas."""

from pydantic import BaseModel


class ConceptMastery(BaseModel):
    concept: str
    level: float  # 0–100
    last_reviewed: str | None = None


class MistakeOut(BaseModel):
    concept: str
    error_description: str
    question_text: str
    user_answer: str
    timestamp: str

    model_config = {"from_attributes": True}


class ProgressResponse(BaseModel):
    user_id: str
    topic: str
    streak: int
    concept_mastery: list[ConceptMastery]
    recent_mistakes: list[MistakeOut]


class ChatRequest(BaseModel):
    user_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
