"""
CleanTrack AI — Photo Processing Worker (arq job)
This is the core AI pipeline job.

Pipeline per report:
1. Fetch photo from S3
2. Call AI service → waste_type, confidence, bounding_box, volume
3. Run deduplication check (PostGIS)
4. Score urgency
5. Get dispatch recommendation
6. Reverse geocode address
7. Update report record
8. Trigger hotspot check
9. Send push notification to reporter
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


async def process_photo_job(
    ctx: dict,
    report_id: str,
    photo_key: str,
    latitude: float,
    longitude: float,
) -> dict:
    """
    Main async photo processing job.
    ctx is injected by arq and contains the shared Redis + DB pool.
    """
    log = logger.bind(report_id=report_id, job="process_photo")
    log.info("photo_processing_started")

    from app.core.database import AsyncSessionLocal
    from app.models.report import Report, ReportStatus
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        # 1. Fetch report
        result = await db.execute(select(Report).where(Report.id == uuid.UUID(report_id)))
        report = result.scalar_one_or_none()
        if not report:
            log.error("report_not_found")
            return {"status": "error", "reason": "report_not_found"}

        try:
            # 2. Call AI microservice
            ai_result = await _call_ai_service(photo_key, latitude, longitude)
            if not ai_result:
                raise ValueError("AI service returned empty response")

            log.info("ai_result_received", waste_type=ai_result.get("waste_type"))

            # 3. Update report with AI output
            from app.models.report import WasteType
            report.waste_type = WasteType(ai_result.get("waste_type", "unknown"))
            report.ai_confidence = ai_result.get("confidence", 0.0)
            report.ai_bounding_box = ai_result.get("bounding_box")
            report.volume_estimate_m3 = ai_result.get("volume_estimate_m3", 0.0)
            report.ai_raw_output = ai_result
            report.status = ReportStatus.AI_PROCESSED

            # 4. Deduplication
            from app.services.dedup_service import DedupService
            dedup_svc = DedupService(db)
            duplicate = await dedup_svc.find_duplicate(latitude, longitude, report.waste_type)

            if duplicate:
                await dedup_svc.mark_duplicate(report, duplicate)
                log.info("duplicate_detected", original_id=str(duplicate.id))
            else:
                # 5. Urgency score
                report.urgency_score = ai_result.get("urgency_score", 50)
                report.recommended_vehicle = ai_result.get("recommended_vehicle")
                report.recommended_team_size = ai_result.get("recommended_team_size", 2)

                # 6. Reverse geocode
                from app.services.maps_service import MapsService
                maps = MapsService()
                geo = await maps.reverse_geocode(latitude, longitude)
                report.address = geo.get("address")
                report.city = geo.get("city")
                report.district = geo.get("district")

            await db.commit()

            # 7. Notify reporter
            if report.reporter_id:
                await _notify_reporter(report, db, duplicate is not None)

            # 8. Check if hotspot recompute needed
            await _maybe_trigger_hotspot_recompute(ctx.get("redis"))

            log.info("photo_processing_completed", status=report.status.value)
            return {"status": "success", "report_id": report_id}

        except Exception as e:
            log.error("photo_processing_failed", error=str(e))
            report.status = ReportStatus.PENDING_AI  # Reset for retry
            await db.commit()
            raise


async def _call_ai_service(photo_key: str, lat: float, lng: float) -> Optional[dict]:
    """Call the internal AI microservice."""
    url = f"{settings.ai_service_url}/analyze"
    payload = {"photo_key": photo_key, "latitude": lat, "longitude": lng}

    async with httpx.AsyncClient(timeout=settings.ai_service_timeout_seconds) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


async def _notify_reporter(report, db, is_duplicate: bool) -> None:
    """Send push notification to the citizen who submitted the report."""
    try:
        from app.services.notification_service import NotificationService
        from app.models.notification import NotificationType
        from app.models.user import User
        from sqlalchemy import select

        result = await db.execute(select(User).where(User.id == report.reporter_id))
        reporter = result.scalar_one_or_none()
        if not reporter:
            return

        if is_duplicate:
            title = "🔄 Report Merged"
            body = "Your report matches an existing issue. We're already on it!"
        else:
            title = "🤖 AI Analysis Complete"
            body = f"Waste identified: {report.waste_type.value.title()}. Urgency score: {report.urgency_score}/100"

        notif = NotificationService(db)
        await notif.send_push(
            user=reporter,
            notif_type=NotificationType.AI_PROCESSED,
            title=title,
            body=body,
            payload={"report_id": str(report.id)},
            report_id=report.id,
        )
    except Exception as e:
        logger.error("notify_reporter_failed", error=str(e))


async def _maybe_trigger_hotspot_recompute(redis) -> None:
    """Enqueue hotspot recompute if not recently done."""
    if redis:
        key = "ct:hotspot:last_recompute"
        last = await redis.get(key)
        if not last:
            await redis.setex(key, 1800, "1")  # 30 min cooldown
            # Enqueue the recompute job
            import arq
            # The worker pool will pick this up automatically
            pass  # hotspot_recompute_job runs on cron schedule in WorkerSettings


async def enqueue_photo_processing(
    report_id: str,
    photo_key: str,
    latitude: float,
    longitude: float,
) -> None:
    """Enqueue the photo processing job via arq."""
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        redis_settings = RedisSettings.from_dsn(settings.redis_url)
        pool = await create_pool(redis_settings)
        await pool.enqueue_job(
            "process_photo_job",
            report_id=report_id,
            photo_key=photo_key,
            latitude=latitude,
            longitude=longitude,
        )
        await pool.close()
    except Exception as e:
        logger.error("enqueue_photo_failed", error=str(e))
