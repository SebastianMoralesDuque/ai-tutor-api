"""Pytest fixtures for AI Tutor API tests."""

import os

# Override DATABASE_URL before importing app — tests use local SQLite
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_ai_tutor.db")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)
