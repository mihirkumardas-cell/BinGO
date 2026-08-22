"""
CleanTrack AI — Deduplication Service
Checks if a new report is a duplicate of a nearby recent one.
Uses PostGIS ST_DWithin to find reports within DEDUP_RADIUS_METERS
of the same waste type within DEDUP_WINDOW_HOURS.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.report import Report, ReportStatus, WasteType

settings = get_settings()


class DedupService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_duplicate(
        self,
        lat: float,
        lng: float,
        waste_type: WasteType,
    ) -> Optional[Report]:
        """
        Return the most recent existing report within DEDUP_RADIUS_METERS
        of the same waste type, submitted within DEDUP_WINDOW_HOURS.
        Returns None if no duplicate found.
        """
        from geoalchemy2.functions import ST_DWithin, ST_SetSRID, ST_MakePoint
        from sqlalchemy import cast
        from geoalchemy2.types import Geography

        cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.dedup_window_hours)
        point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)

        query = (
            select(Report)
            .where(
                ST_DWithin(
                    cast(Report.location, Geography),
                    cast(point, Geography),
                    settings.dedup_radius_meters,
                )
            )
            .where(Report.waste_type == waste_type)
            .where(Report.created_at >= cutoff)
            .where(Report.status.notin_([ReportStatus.REJECTED, ReportStatus.RESOLVED]))
            .where(Report.is_duplicate == False)  # Only check originals
            .order_by(Report.created_at.desc())
            .limit(1)
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def mark_duplicate(
        self,
        report: Report,
        original: Report,
    ) -> None:
        """Mark report as duplicate and increment the original's recurrence count."""
        report.is_duplicate = True
        report.duplicate_of_id = original.id
        report.status = ReportStatus.DUPLICATE

        # Increment recurrence counter on the original
        original.recurrence_count = (original.recurrence_count or 1) + 1
