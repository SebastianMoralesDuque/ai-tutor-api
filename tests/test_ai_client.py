"""Tests for AI client implementations."""

import pytest

from app.core.ai_client import MockAIClient


@pytest.mark.asyncio
async def test_mock_generate_lesson():
    """MockAIClient.generate_lesson returns a structured lesson dict."""
    client = MockAIClient()
    result = await client.generate_lesson("math", ["algebra"], [], 20)
    assert "title" in result
    assert "explanation" in result
    assert "bullets" in result
    assert "example" in result


@pytest.mark.asyncio
async def test_mock_generate_quiz():
    """MockAIClient.generate_quiz returns a list of quiz questions."""
    client = MockAIClient()
    lesson = {"title": "Algebra", "explanation": "Study of symbols.", "bullets": [], "example": ""}
    result = await client.generate_quiz("math", lesson, ["algebra"], [])
    assert isinstance(result, list)
    if result:
        q = result[0]
        assert "question_id" in q
        assert "question" in q
        assert "options" in q
        assert "correct_answer_index" in q


@pytest.mark.asyncio
async def test_mock_evaluate_answer():
    """MockAIClient.evaluate_answer returns correct/feedback dict."""
    client = MockAIClient()
    result = await client.evaluate_answer("What is 2+2?", ["4", "5", "6", "7"], "0")
    assert "correct" in result
    assert "feedback" in result
    assert result["correct"] is True


@pytest.mark.asyncio
async def test_mock_chat():
    """MockAIClient.chat returns a helpful response string."""
    client = MockAIClient()
    result = await client.chat("What is algebra?", {"topic": "math"})
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_mock_chat_completion():
    """MockAIClient.chat_completion returns a JSON string."""
    client = MockAIClient()
    result = await client.chat_completion([{"role": "user", "content": "Hello"}])
    assert isinstance(result, str)
