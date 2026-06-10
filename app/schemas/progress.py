"""Progress and chat schemas."""

from pydantic import BaseModel


class ConceptMastery(BaseModel):
    concept: str
    level: float  # 0–100
    sessions_done: int = 0
    completed: bool = False
    is_current: bool = False


class MistakeOut(BaseModel):
    concept: str
    error_description: str
    question_text: str
    user_answer: str
    timestamp: str

    model_config = {"from_attributes": True}


class CycleInfo(BaseModel):
    concept_index: int
    day_in_cycle: int
    total_concepts: int
    days_per_concept: int


class TopicProgressOut(BaseModel):
    topic: str
    status: str
    concepts_completed: int
    started_at: str | None = None


class CompletedTopicOut(BaseModel):
    topic: str
    completed_at: str | None = None


class ProgressResponse(BaseModel):
    user_id: str
    current_topic: str
    streak: int
    cycle: CycleInfo
    topic_progress: TopicProgressOut | None = None
    concept_mastery: list[ConceptMastery]
    completed_topics: list[CompletedTopicOut]
    recent_mistakes: list[MistakeOut]


class ChatRequest(BaseModel):
    user_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
