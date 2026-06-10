"""
AI client abstraction.

OpenCode Zen (DeepSeek V4 Flash Free) — no API key required.
Uses httpx for direct HTTP calls, zero external AI SDKs.
"""

import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx


@dataclass
class AIResponse:
    content: str
    parsed: dict | None = None


class AIClient(ABC):
    """Abstract base — all AI providers implement this."""

    @abstractmethod
    def generate_lesson(
        self, topic: str, concepts: list[str], mistakes: list[dict], daily_time: int,
        day_in_cycle: int = 1, concept_type: str = "fundamentals",
    ) -> dict:
        """Generate a structured lesson block."""

    @abstractmethod
    def generate_quiz(
        self, topic: str, lesson: dict, concepts: list[str], mistakes: list[dict]
    ) -> list[dict]:
        """Generate quiz questions based on the lesson."""

    @abstractmethod
    def evaluate_answer(self, question: str, options: list[str], answer: str) -> dict:
        """Evaluate a user's answer. Returns {correct, feedback, concept}."""

    @abstractmethod
    def chat(self, message: str, context: dict) -> str:
        """Free-form tutor chat with memory context."""


# ── Mock Client (for testing without network) ────────────────────────


class MockAIClient(AIClient):
    """
    Deterministic mock for development and testing.
    Returns structured JSON without any API calls.
    """

    def generate_lesson(
        self, topic: str, concepts: list[str], mistakes: list[dict], daily_time: int,
        day_in_cycle: int = 1, concept_type: str = "fundamentals",
    ) -> dict:
        weak_concepts = [m.get("concept", "a concept") for m in mistakes[:3]]
        focus = ", ".join(weak_concepts) if weak_concepts else ", ".join(concepts[:3])

        return {
            "title": f"Understanding {topic}: {focus}",
            "explanation": (
                f"Today we're diving deeper into {topic}. "
                f"We'll focus on {focus} — areas where you've had some difficulty. "
                f"This lesson is designed for your {daily_time}-minute study session."
            ),
            "bullets": [
                f"Key concept: {c}" for c in (concepts[:4] or ["Core fundamentals"])
            ] + (
                [f"Review: {m.get('concept', 'previous mistake')}" for m in mistakes[:2]]
                if mistakes
                else []
            ),
            "example": (
                f"For example, in {topic}, when you encounter "
                f"{concepts[0] if concepts else 'this concept'}, "
                f"remember to apply the fundamental principle step by step."
            ),
        }

    def generate_quiz(
        self, topic: str, lesson: dict, concepts: list[str], mistakes: list[dict]
    ) -> list[dict]:
        questions = []

        for i, concept in enumerate(concepts[:4]):
            questions.append({
                "question_id": f"q_{uuid.uuid4().hex[:8]}",
                "question": f"In the context of {topic}, what best describes {concept}?",
                "options": [
                    f"The correct understanding of {concept}",
                    f"A common misconception about {concept}",
                    f"An unrelated concept to {concept}",
                    f"None of the above",
                ],
                "correct_answer_index": 0,
                "answer_type": "multiple_choice",
                "_concept": concept,
            })

        if mistakes:
            m = mistakes[0]
            questions.append({
                "question_id": f"q_{uuid.uuid4().hex[:8]}",
                "question": f"Regarding {m.get('concept', topic)}: {m.get('error_description', 'review this concept')}",
                "options": [
                    "The corrected understanding",
                    "The original mistaken answer",
                    "An unrelated option",
                    "None of the above",
                ],
                "correct_answer_index": 0,
                "answer_type": "multiple_choice",
                "_concept": m.get("concept", topic),
            })

        return questions[:5]

    def evaluate_answer(self, question: str, options: list[str], answer: str) -> dict:
        first_option = options[0] if options else ""
        correct = answer.strip() in ("0", "a", "A") or answer.strip() == first_option

        return {
            "correct": correct,
            "feedback": (
                "Correct! Well done." if correct
                else f"Not quite. The answer is: {options[0] if options else 'review this concept'}. "
                     f"Try to understand why this is the right answer."
            ),
        }

    def chat(self, message: str, context: dict) -> str:
        topic = context.get("topic", "your topic")
        weak = context.get("weak_concepts", [])
        streak = context.get("streak", 0)

        weak_str = ", ".join(weak) if weak else ""
        streak_str = f"You're on a {streak}-day streak — keep it up! " if streak > 0 else ""
        notice_str = f"I notice you've struggled with {weak_str}. " if weak else ""

        return (
            f"Great question about {topic}! "
            f"{notice_str}"
            f"{streak_str}"
            f"Based on what you're asking: {message} — "
            f"let me break this down for you in a way that builds on what you already know."
        )


# ── OpenCode Zen Client (DeepSeek V4 Flash Free, no key) ────────────


class OpenCodeClient(AIClient):
    """
    OpenCode Zen client for DeepSeek V4 Flash Free.
    No API key required. Uses plain HTTP via httpx.
    """

    def __init__(self, model: str = "deepseek-v4-flash-free", base_url: str = "https://opencode.ai/zen/v1"):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=60.0)

    def _chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """Low-level chat completion call."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = self.client.post(f"{self.base_url}/chat/completions", json=payload)
        response.raise_for_status()

        data = response.json()
        choice = data["choices"][0]
        message = choice["message"]

        # DeepSeek returns reasoning_content separately; prefer content
        content = message.get("content") or ""
        reasoning = message.get("reasoning_content") or ""

        # If content is empty (tokens went to reasoning), use reasoning
        return content if content.strip() else reasoning

    def _parse_json(self, text: str) -> dict | list:
        """Extract JSON from AI response, handling markdown fences."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        # Try to find JSON object or array in the text
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = cleaned.find(start_char)
            end = cleaned.rfind(end_char)
            if start != -1 and end > start:
                try:
                    return json.loads(cleaned[start:end + 1])
                except json.JSONDecodeError:
                    continue

        return json.loads(cleaned)

    def generate_lesson(
        self, topic: str, concepts: list[str], mistakes: list[dict], daily_time: int,
        day_in_cycle: int = 1, concept_type: str = "fundamentals",
    ) -> dict:
        from app.core.prompt_builder import build_lesson_prompt

        prompt = build_lesson_prompt(topic, concepts, mistakes, daily_time, day_in_cycle, concept_type)
        messages = [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]},
        ]

        try:
            raw = self._chat(messages, temperature=0.7)
            return self._parse_json(raw)
        except Exception:
            return {
                "title": f"Lesson: {topic}",
                "explanation": f"Learning about {topic}",
                "bullets": [f"Concept: {c}" for c in concepts[:4]],
                "example": f"Example for {topic}: apply these concepts step by step.",
            }

    def generate_quiz(
        self, topic: str, lesson: dict, concepts: list[str], mistakes: list[dict]
    ) -> list[dict]:
        from app.core.prompt_builder import build_quiz_prompt

        prompt = build_quiz_prompt(topic, lesson, concepts, mistakes)
        messages = [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]},
        ]

        try:
            raw = self._chat(messages, temperature=0.6)
            parsed = self._parse_json(raw)

            if not isinstance(parsed, list):
                return []

            questions = []
            for i, q in enumerate(parsed):
                # Validate structure
                question_text = q.get("question", "").strip()
                options = q.get("options", [])
                correct_index = q.get("correct_index", -1)
                concept = q.get("concept", concepts[i] if i < len(concepts) else topic)

                # Skip invalid questions
                if not question_text or len(options) != 4:
                    continue
                if not isinstance(correct_index, int) or correct_index not in (0, 1, 2, 3):
                    continue

                questions.append({
                    "question_id": f"q_{uuid.uuid4().hex[:8]}",
                    "question": question_text,
                    "options": options,
                    "correct_answer_index": correct_index,
                    "answer_type": "multiple_choice",
                    "_concept": concept,
                })

            return questions[:5]
        except Exception:
            return []

    def evaluate_answer(self, question: str, options: list[str], answer: str) -> dict:
        messages = [
            {
                "role": "system",
                "content": (
                    "Eres un evaluador de cuestionarios. Dada una pregunta, opciones y la respuesta "
                    "del estudiante, evalúa si es correcta. Devuelve JSON: {\"correct\": bool, \"feedback\": str}. "
                    "Sé alentador pero preciso. Responde siempre en español."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Pregunta: {question}\n"
                    f"Opciones: {json.dumps(options)}\n"
                    f"Respuesta del estudiante: {answer}\n"
                    "Evalúa y devuelve JSON."
                ),
            },
        ]

        try:
            raw = self._chat(messages, temperature=0.3)
            return self._parse_json(raw)
        except Exception:
            return {"correct": False, "feedback": "Could not evaluate. Please try again."}

    def chat(self, message: str, context: dict) -> str:
        from app.core.prompt_builder import build_chat_prompt

        prompt = build_chat_prompt(message, context)
        messages = [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]},
        ]

        try:
            return self._chat(messages, temperature=0.7)
        except Exception:
            return "I'm having trouble connecting to my knowledge base. Please try again."


# ── Factory ──────────────────────────────────────────────────────────


def get_ai_client() -> AIClient:
    """Factory — returns the configured AI client."""
    from app.core.config import settings

    if settings.AI_PROVIDER == "mock":
        return MockAIClient()
    if settings.AI_PROVIDER == "opencode":
        return OpenCodeClient(
            model=settings.AI_MODEL,
            base_url=settings.AI_BASE_URL,
        )
    return MockAIClient()
