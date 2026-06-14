"""
AI Tutor Backend — FastAPI application entry point.

Run with: uvicorn app.main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.core.ai_client import get_ai_client
from app.core.config import limiter, settings
from app.db.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ai-tutor")

# Ensure tables exist at import time (works with TestClient and uvicorn)
init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables (idempotent). Shutdown: close AI client connections."""
    logger.info("Starting %s v%s", settings.APP_NAME, settings.VERSION)
    init_db()
    yield
    # Close AI client connections on shutdown
    try:
        client = get_ai_client()
        await client.close()
    except Exception:
        logger.warning("Error closing AI client", exc_info=True)
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — allow Android app origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=False,  # Can't use credentials with wildcard origin
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routes ──────────────────────────────────────────────────
from app.api.routes.user import router as user_router
from app.api.routes.learning import router as learning_router
from app.api.routes.chat import router as chat_router
from app.api.routes.suggestions import router as suggestions_router

app.include_router(user_router)
app.include_router(learning_router)
app.include_router(chat_router)
app.include_router(suggestions_router)


@app.get("/health")
def health():
    return {"status": "ok", "version": settings.VERSION}
