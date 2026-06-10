"""Suggestion schemas."""

from pydantic import BaseModel


class SuggestionRequest(BaseModel):
    user_id: str
