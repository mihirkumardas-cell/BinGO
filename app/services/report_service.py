"""
CleanTrack AI — Report Service
Handles creation, listing, verification, and closure of waste reports.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundException
from app.core.storage import upload_dispatch_photo, get_photo_url
from app.models.report import Report, ReportStatus, WasteType
from app.models.user import User
from app.schemas.report import (
    ReportCreateRequest, ReportListResponse, ReportResponse,
    ReportVerifyRequest, ReportCloseRequest
)

settings = get_settings()


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        data: ReportCreateRequest,
        reporter: User,
        photo_key: Optional[str] = None,
        photo_url: Optional[str] = None,
        thumbnail_key: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
    ) -> Report:
        """Create a new report. Photo processing is handled asynchronously by worker."""
        from geoalchemy2.elements import WKTElement

        point_wkt = f"POINT({data.longitude} {data.latitude})"

        report = Report(
            reporter_id=reporter.id,
            latitude=data.latitude,
            longitude=data.longitude,
            location=WKTElement(point_wkt, srid=4326),
            description=data.description,
            photo_key=photo_key,
            photo_url=photo_url,
            thumbnail_key=thumbnail_key,
            thumbnail_url=thumbnail_url,
            status=ReportStatus.PENDING_AI,
        )
        self.db.add(report)
        await self.db.flush()
        return report

    async def get_by_id(self, report_id: uuid.UUID) -> Report:
        result = await self.db.execute(
            select(Report).where(Report.id == report_id)
        )
        report = result.scalar_one_or_none()
        if not report:
            raise NotFoundException("Report", str(report_id))
        return report

    async def list_reports(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[ReportStatus] = None,
        waste_type: Optional[WasteType] = None,
        reporter_id: Optional[uuid.UUID] = None,
        hotspot_id: Optional[uuid.UUID] = None,
        min_urgency: Optional[int] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,  # (min_lat, min_lng, max_lat, max_lng)
    ) -> ReportListResponse:
        from geoalchemy2.functions import ST_Within, ST_MakeEnvelope

        query = select(Report).order_by(desc(Report.created_at))

        if status:
            query = query.where(Report.status == status)
        if waste_type:
            query = query.where(Report.waste_type == waste_type)
        if reporter_id:
            query = query.where(Report.reporter_id == reporter_id)
        if hotspot_id:
            query = query.where(Report.hotspot_id == hotspot_id)
        if min_urgency is not None:
            query = query.where(Report.urgency_score >= min_urgency)
        if bbox:
            min_lat, min_lng, max_lat, max_lng = bbox
            envelope = ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326)
            query = query.where(ST_Within(Report.location, envelope))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        # Paginate
        offset = (page - 1) * page_size
        result = await self.db.execute(query.offset(offset).limit(page_size))
        reports = result.scalars().all()

        return ReportListResponse(
            items=reports,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(offset + page_size) < total,
        )

    async def verify(
        self, report_id: uuid.UUID, data: ReportVerifyRequest, admin: User
    ) -> Report:
        report = await self.get_by_id(report_id)

        if data.is_rejected:
            report.status = ReportStatus.REJECTED
            report.admin_notes = data.rejection_reason or data.admin_notes
        else:
            if data.waste_type:
                report.waste_type = data.waste_type
            if data.volume_estimate_m3 is not None:
                report.volume_estimate_m3 = data.volume_estimate_m3
            if data.urgency_score is not None:
                report.urgency_score = data.urgency_score
            if data.admin_notes:
                report.admin_notes = data.admin_notes
            report.status = ReportStatus.VERIFIED
            report.verified_by_id = admin.id
            report.verified_at = datetime.now(timezone.utc)

        return report

    async def close(
        self,
        report_id: uuid.UUID,
        agent: User,
        after_photo_bytes: Optional[bytes] = None,
        completion_notes: Optional[str] = None,
    ) -> Report:
        report = await self.get_by_id(report_id)

        if after_photo_bytes:
            from app.core.storage import upload_dispatch_photo, get_photo_url
            # Find the dispatch assignment for this report
            from app.models.dispatch import DispatchAssignment
            result = await self.db.execute(
                select(DispatchAssignment).where(DispatchAssignment.report_id == report_id)
            )
            dispatch = result.scalar_one_or_none()
            if dispatch:
                key = await upload_dispatch_photo(
                    after_photo_bytes, str(dispatch.id), "after"
                )
                dispatch.after_photo_key = key
                dispatch.after_photo_url = get_photo_url(key)

        report.status = ReportStatus.RESOLVED
        report.resolved_at = datetime.now(timezone.utc)
        return report

    async def get_nearby_reports(
        self,
        lat: float,
        lng: float,
        radius_meters: float = 500,
        limit: int = 10,
    ) -> List[Report]:
        """Find reports within radius (metres) of given coordinates."""
        from geoalchemy2.functions import ST_DWithin, ST_SetSRID, ST_MakePoint
        from sqlalchemy import cast
        from geoalchemy2.types import Geography

        point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)
        query = (
            select(Report)
            .where(
                ST_DWithin(
                    cast(Report.location, Geography),
                    cast(point, Geography),
                    radius_meters,
                )
            )
            .where(Report.status != ReportStatus.REJECTED)
            .order_by(desc(Report.created_at))
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
