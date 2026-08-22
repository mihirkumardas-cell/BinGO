"""
CleanTrack AI — Hotspot Recompute Worker (arq cron job)
Runs DBSCAN clustering every 30 minutes to update hotspots.
"""
import structlog

logger = structlog.get_logger()


async def hotspot_recompute_job(ctx: dict) -> dict:
    """
    DBSCAN recompute over all recent non-duplicate reports.
    Updates existing hotspots and creates new ones.
    """
    logger.info("hotspot_recompute_started")

    from app.core.database import AsyncSessionLocal
    from app.services.hotspot_service import HotspotService

    async with AsyncSessionLocal() as db:
        try:
            service = HotspotService(db)
            count = await service.recompute_all()
            logger.info("hotspot_recompute_completed", hotspots_processed=count)
            return {"status": "success", "hotspots_processed": count}
        except Exception as e:
            logger.error("hotspot_recompute_failed", error=str(e))
            raise
