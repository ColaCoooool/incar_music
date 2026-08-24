"""InCar Music - Main application."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import settings
from models.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting InCar Music server...")

    # Ensure directories exist
    Path(settings.CACHE_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.HLS_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.COVER_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")).parent.mkdir(
        parents=True, exist_ok=True
    )

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    yield

    logger.info("Shutting down InCar Music server...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
from api.songs import router as songs_router
from api.streaming import router as streaming_router
from api.library import router as library_router
from api.covers import router as covers_router
from api.lyrics import router as lyrics_router
from api.scraper import router as scraper_router

app.include_router(songs_router)
app.include_router(streaming_router)
app.include_router(library_router)
app.include_router(covers_router)
app.include_router(lyrics_router)
app.include_router(scraper_router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "music_library": settings.MUSIC_LIBRARY_PATH,
    }


# Serve frontend static files (if built)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
