"""Learning session schemas."""

from typing import Literal

from pydantic import BaseModel, Field


# ── Daily Session ────────────────────────────────────────────────────

class LessonBlock(BaseModel):
    title: str
    explanation: str
    bullets: list[str]
    example: str


class QuizQuestion(BaseModel):
    question_id: str
    question: str
    options: list[str]
    correct_answer_index: int = -1
    answer_type: Literal["multiple_choice"] = "multiple_choice"


class CycleInfo(BaseModel):
    topic: str
    concept: str
    concept_index: int
    day_in_cycle: int
    total_concepts: int
    topic_completed: bool


class DailySessionRequest(BaseModel):
    user_id: str


class DailySessionResponse(BaseModel):
    lesson: LessonBlock
    quiz: list[QuizQuestion]
    cycle_info: CycleInfo


# ── Submit Answer ────────────────────────────────────────────────────

class SubmitAnswerRequest(BaseModel):
    user_id: str
    question_id: str
    answer: str


class SubmitAnswerResponse(BaseModel):
    correct: bool
    feedback: str
    concept: str
    mastery_delta: float
    updated_progress: dict
