"""
CleanTrack AI — Hotspot Service
Runs DBSCAN clustering on recent unresolved reports to find/update hotspots.
Executed by the hotspot_recompute background worker every 30 minutes.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.hotspot import Hotspot, HotspotSeverity
from app.models.report import Report, ReportStatus, WasteType

settings = get_settings()

# Earth radius for haversine (metres per degree at equator)
METRES_PER_DEGREE = 111_320.0


def _severity_from_count(count: int) -> HotspotSeverity:
    if count >= 21:
        return HotspotSeverity.CRITICAL
    if count >= 11:
        return HotspotSeverity.HIGH
    if count >= 6:
        return HotspotSeverity.MEDIUM
    return HotspotSeverity.LOW


class HotspotService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def recompute_all(self) -> int:
        """
        Full DBSCAN recompute over recent non-duplicate reports.
        Returns the number of hotspots created or updated.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.hotspot_window_days)

        result = await self.db.execute(
            select(Report)
            .where(Report.created_at >= cutoff)
            .where(Report.is_duplicate == False)
            .where(Report.status.notin_([ReportStatus.REJECTED]))
        )
        reports: List[Report] = result.scalars().all()

        if len(reports) < settings.hotspot_min_reports:
            return 0

        # Prepare coordinate matrix [lat, lng]
        coords = np.array([[r.latitude, r.longitude] for r in reports])

        # DBSCAN with haversine-like epsilon
        # eps in degrees (approx) for HOTSPOT_RADIUS_METERS
        eps_deg = settings.hotspot_radius_meters / METRES_PER_DEGREE

        db = DBSCAN(
            eps=eps_deg,
            min_samples=settings.hotspot_min_reports,
            algorithm="ball_tree",
            metric="haversine",
        )
        # DBSCAN with haversine expects radians
        coords_rad = np.radians(coords)
        eps_rad = settings.hotspot_radius_meters / 6_371_000  # Earth radius in metres
        db_rad = DBSCAN(eps=eps_rad, min_samples=settings.hotspot_min_reports,
                        algorithm="ball_tree", metric="haversine")
        labels = db_rad.fit_predict(coords_rad)

        unique_labels = set(labels) - {-1}  # -1 = noise
        processed = 0

        for label in unique_labels:
            mask = labels == label
            cluster_reports = [r for r, m in zip(reports, mask) if m]

            centroid_lat = float(np.mean([r.latitude for r in cluster_reports]))
            centroid_lng = float(np.mean([r.longitude for r in cluster_reports]))

            dominant_type = self._dominant_waste_type(cluster_reports)
            avg_urgency = float(np.mean([r.urgency_score or 0 for r in cluster_reports]))
            report_count = len(cluster_reports)
            severity = _severity_from_count(report_count)

            # Try to update existing hotspot near this centroid
            hotspot = await self._find_nearby_hotspot(centroid_lat, centroid_lng)

            if hotspot:
                hotspot.centroid_lat = centroid_lat
                hotspot.centroid_lng = centroid_lng
                from geoalchemy2.elements import WKTElement
                hotspot.centroid = WKTElement(f"POINT({centroid_lng} {centroid_lat})", srid=4326)
                hotspot.report_count = report_count
                hotspot.severity = severity
                hotspot.dominant_waste_type = dominant_type
                hotspot.avg_urgency_score = avg_urgency
                hotspot.cluster_label = label
                hotspot.last_reported_at = max(r.created_at for r in cluster_reports)
                hotspot.last_recomputed_at = datetime.now(timezone.utc)
            else:
                from geoalchemy2.elements import WKTElement
                hotspot = Hotspot(
                    centroid=WKTElement(f"POINT({centroid_lng} {centroid_lat})", srid=4326),
                    centroid_lat=centroid_lat,
                    centroid_lng=centroid_lng,
                    report_count=report_count,
                    severity=severity,
                    dominant_waste_type=dominant_type,
                    avg_urgency_score=avg_urgency,
                    cluster_label=label,
                    first_reported_at=min(r.created_at for r in cluster_reports),
                    last_reported_at=max(r.created_at for r in cluster_reports),
                    radius_meters=settings.hotspot_radius_meters,
                )
                self.db.add(hotspot)
                await self.db.flush()

            # Link reports to hotspot
            for r in cluster_reports:
                r.hotspot_id = hotspot.id

            processed += 1

        await self.db.commit()
        return processed

    async def _find_nearby_hotspot(self, lat: float, lng: float) -> Optional[Hotspot]:
        from geoalchemy2.functions import ST_DWithin, ST_SetSRID, ST_MakePoint
        from sqlalchemy import cast
        from geoalchemy2.types import Geography

        point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)
        result = await self.db.execute(
            select(Hotspot)
            .where(
                ST_DWithin(
                    cast(Hotspot.centroid, Geography),
                    cast(point, Geography),
                    settings.hotspot_radius_meters,
                )
            )
            .where(Hotspot.is_active == True)
            .limit(1)
        )
        return result.scalar_one_or_none()

    def _dominant_waste_type(self, reports: List[Report]) -> str:
        from collections import Counter
        types = [r.waste_type.value for r in reports if r.waste_type]
        if not types:
            return WasteType.UNKNOWN.value
        return Counter(types).most_common(1)[0][0]

    async def get_hotspots_in_bbox(
        self,
        min_lat: float, min_lng: float,
        max_lat: float, max_lng: float,
        severity: Optional[HotspotSeverity] = None,
    ) -> List[Hotspot]:
        from geoalchemy2.functions import ST_Within, ST_MakeEnvelope

        envelope = ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326)
        query = (
            select(Hotspot)
            .where(ST_Within(Hotspot.centroid, envelope))
            .where(Hotspot.is_active == True)
        )
        if severity:
            query = query.where(Hotspot.severity == severity)

        result = await self.db.execute(query)
        return result.scalars().all()
