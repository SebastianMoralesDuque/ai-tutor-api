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
    answer_type: Literal["multiple_choice"] = "multiple_choice"


class DailySessionRequest(BaseModel):
    user_id: str


class DailySessionResponse(BaseModel):
    lesson: LessonBlock
    quiz: list[QuizQuestion]


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
