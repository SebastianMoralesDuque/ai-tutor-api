"""
AI Tutor Backend — FastAPI application entry point.

Run with: uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import init_db

# Ensure tables exist at import time (works with TestClient and uvicorn)
init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables (idempotent). Shutdown: nothing special."""
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

# CORS — allow Android app origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routes ──────────────────────────────────────────────────
from app.api.routes.user import router as user_router
from app.api.routes.learning import router as learning_router
from app.api.routes.chat import router as chat_router

app.include_router(user_router)
app.include_router(learning_router)
app.include_router(chat_router)


@app.get("/health")
def health():
    return {"status": "ok", "version": settings.VERSION}
