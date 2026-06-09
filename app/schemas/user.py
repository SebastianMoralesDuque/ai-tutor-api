"""User schemas for request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    topic: str = Field(..., min_length=1, max_length=255, description="Topic of study")
    daily_time: int = Field(20, ge=5, le=120, description="Daily study time in minutes")


class UserResponse(BaseModel):
    id: str
    topic: str
    daily_time: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    topic: Optional[str] = Field(None, max_length=255)
    daily_time: Optional[int] = Field(None, ge=5, le=120)
