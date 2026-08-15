"""
CleanTrack AI — arq Worker Settings
Defines all available jobs and cron schedules.
"""
from arq import cron

from app.core.config import get_settings
from app.workers.photo_processor import process_photo_job
from app.workers.hotspot_recompute import hotspot_recompute_job

settings = get_settings()


async def startup(ctx):
    """Called once when the worker starts."""
    import structlog
    logger = structlog.get_logger()
    logger.info("cleantrack_worker_started")


async def shutdown(ctx):
    """Called when the worker shuts down."""
    import structlog
    logger = structlog.get_logger()
    logger.info("cleantrack_worker_shutdown")


class WorkerSettings:
    """arq Worker configuration."""

    # Redis connection
    redis_settings = None  # Populated dynamically below

    # All available job functions
    functions = [
        process_photo_job,
        hotspot_recompute_job,
    ]

    # Cron schedules
    cron_jobs = [
        # Recompute hotspots every 30 minutes
        cron(hotspot_recompute_job, minute={0, 30}),
    ]

    # Worker settings
    max_jobs = 10
    job_timeout = 300  # 5 minutes max per job
    keep_result = 86400  # Keep job results for 24h
    retry_jobs = True
    max_tries = 3

    on_startup = startup
    on_shutdown = shutdown


# Build Redis settings from config
from arq.connections import RedisSettings
WorkerSettings.redis_settings = RedisSettings.from_dsn(settings.redis_url)
