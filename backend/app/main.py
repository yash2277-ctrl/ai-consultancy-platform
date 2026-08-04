"""
AI Consultancy Platform — FastAPI Entry Point
==============================================
Production-ready backend for an AI-powered management consultancy.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.auth.router import router as auth_router
from app.upload.router import router as upload_router
from app.consult.router import router as consult_router

settings = get_settings()

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting AI Consultancy Platform v%s", settings.APP_VERSION)
    await init_db()
    logger.info("✅ Database tables initialised")
    yield
    logger.info("🛑 Shutting down")


# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-powered management consultancy platform providing financial analysis, "
        "market strategy, and executive-level consulting reports using multi-agent AI."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(consult_router, prefix="/api")


# ── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "service": settings.APP_NAME,
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "AI Consultancy Platform API",
        "docs": "/docs",
        "version": settings.APP_VERSION,
    }
