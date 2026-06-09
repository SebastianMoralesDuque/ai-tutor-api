"""
Prompt builder — constructs structured prompts for the AI layer.

Separate from the AI client so prompts are testable and tunable
without changing the provider.

IMPORTANT: All system prompts end with "Answer directly without thinking out loud.
Output ONLY the JSON, no markdown fences, no extra text." because DeepSeek V4
uses reasoning_content internally — if we don't force direct output, all max_tokens
get consumed by thinking and content comes back empty.
"""


def build_lesson_prompt(
    topic: str,
    concepts: list[str],
    mistakes: list[dict],
    daily_time: int,
) -> dict:
    """
    Build a prompt payload for lesson generation.
    Returns a dict with system + user messages.
    """
    mistake_context = ""
    if mistakes:
        items = "\n".join(
            f"- {m.get('concept', 'unknown')}: {m.get('error_description', '')}"
            for m in mistakes[:5]
        )
        mistake_context = f"\nThe student has made these recent mistakes:\n{items}\n"

    return {
        "system": (
            "You are an expert tutor. Generate a concise, structured lesson. "
            "The lesson should be suitable for a focused study session. "
            "Return JSON with: title, explanation, bullets (list), example. "
            "Answer directly without thinking out loud. "
            "Output ONLY the JSON, no markdown fences, no extra text."
        ),
        "user": (
            f"Topic: {topic}\n"
            f"Study time: {daily_time} minutes\n"
            f"Key concepts to cover: {', '.join(concepts)}\n"
            f"{mistake_context}"
            "Generate a structured lesson in JSON format."
        ),
    }


def build_quiz_prompt(
    topic: str,
    lesson: dict,
    mistakes: list[dict],
) -> dict:
    """Build a prompt payload for quiz generation."""
    return {
        "system": (
            "You are a quiz generator. Create multiple-choice questions "
            "that test understanding of the lesson. Return JSON array of objects "
            "with: question, options (4 choices), correct_index. "
            "Answer directly without thinking out loud. "
            "Output ONLY the JSON array, no markdown fences, no extra text."
        ),
        "user": (
            f"Topic: {topic}\n"
            f"Lesson: {lesson.get('title', '')}\n"
            f"Key points: {', '.join(lesson.get('bullets', []))}\n"
            f"Past mistakes to test: "
            f"{[m.get('concept', '') for m in mistakes[:3]]}\n"
            "Generate 3-5 quiz questions."
        ),
    }


def build_chat_prompt(message: str, context: dict) -> dict:
    """Build a prompt for tutor chat with student memory."""
    parts = []
    if context.get("topic"):
        parts.append(f"Student is learning: {context['topic']}")
    if context.get("weak_concepts"):
        parts.append(f"Weak areas: {', '.join(context['weak_concepts'])}")
    if context.get("recent_mistakes"):
        parts.append(
            f"Recent mistakes: {[m.get('error_description', '') for m in context['recent_mistakes'][:3]]}"
        )
    if context.get("streak"):
        parts.append(f"Study streak: {context['streak']} days")

    student_context = "\n".join(parts) if parts else "No prior context available."

    return {
        "system": (
            "You are a patient, encouraging tutor. "
            "Answer the student's question clearly. "
            "Reference their learning history when relevant. "
            "Keep responses concise but helpful. "
            "Answer directly without thinking out loud."
        ),
        "user": (
            f"Student context:\n{student_context}\n\n"
            f"Student asks: {message}"
        ),
    }
