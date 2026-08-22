"""
CleanTrack AI — FastAPI Application Entry Point
"""
import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1 import api_v1_router
from app.core.config import get_settings
from app.core.exceptions import (
    CleanTrackException, cleantrack_exception_handler, generic_exception_handler
)

settings = get_settings()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup → serve → shutdown."""
    logger.info(
        "cleantrack_api_starting",
        env=settings.app_env,
        version="1.0.0",
    )

    # Verify DB connection
    try:
        from app.core.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("database_connection_ok")
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))

    # Verify Redis connection
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        await redis.ping()
        logger.info("redis_connection_ok")
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))

    # Seed initial data if DB is empty
    try:
        from app.core.seed_data import seed_database
        await seed_database()
    except Exception as e:
        logger.error("seed_database_failed", error=str(e))

    yield

    logger.info("cleantrack_api_shutting_down")
    from app.core.redis_client import close_redis
    await close_redis()
    await engine.dispose()


# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="BinGO API",
    description=(
        "AI-powered waste reporting and municipal dispatch platform.\n\n"
        "**Dataset**: [Kaggle Garbage Classification]"
        "(https://www.kaggle.com/datasets/asdasdasasdas/garbage-classification) "
        "+ [TACO Dataset](http://tacoDataset.org/)\n\n"
        "**Roles**: citizen → field_agent → municipal_admin → super_admin"
    ),
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Exception handlers ────────────────────────────────────────────────────────
app.add_exception_handler(CleanTrackException, cleantrack_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(api_v1_router)


# ── Health & readiness endpoints ──────────────────────────────────────────────
@app.get("/health", tags=["System"], include_in_schema=False)
async def health():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/ready", tags=["System"], include_in_schema=False)
async def readiness(request: Request):
    """Kubernetes readiness probe — checks DB and Redis."""
    try:
        from app.core.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        from app.core.redis_client import get_redis
        redis = await get_redis()
        await redis.ping()

        return {"status": "ready"}
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": str(e)},
        )


# ── Static Files (Frontend UI) ────────────────────────────────────────────────
from pathlib import Path
from fastapi.staticfiles import StaticFiles

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

