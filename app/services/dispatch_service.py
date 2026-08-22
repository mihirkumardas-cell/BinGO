"""
CleanTrack AI — Dispatch Service
Assigns sanitation teams to reports/hotspots and manages dispatch lifecycle.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, CleanTrackException
from app.core.storage import upload_dispatch_photo, get_photo_url
from app.models.dispatch import DispatchAssignment, DispatchStatus, VehicleType
from app.models.report import Report, ReportStatus
from app.models.hotspot import Hotspot
from app.models.user import User
from app.schemas.dispatch import DispatchAssignRequest, DispatchUpdateRequest
from app.services.maps_service import MapsService


class DispatchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def assign(
        self,
        data: DispatchAssignRequest,
        admin: User,
    ) -> DispatchAssignment:
        if not data.report_id and not data.hotspot_id:
            raise CleanTrackException("Either report_id or hotspot_id must be provided")

        # Validate target exists
        target_lat, target_lng = None, None
        if data.report_id:
            result = await self.db.execute(select(Report).where(Report.id == data.report_id))
            report = result.scalar_one_or_none()
            if not report:
                raise NotFoundException("Report", str(data.report_id))
            report.status = ReportStatus.DISPATCHED
            target_lat, target_lng = report.latitude, report.longitude
        else:
            result = await self.db.execute(select(Hotspot).where(Hotspot.id == data.hotspot_id))
            hotspot = result.scalar_one_or_none()
            if not hotspot:
                raise NotFoundException("Hotspot", str(data.hotspot_id))
            target_lat, target_lng = hotspot.centroid_lat, hotspot.centroid_lng

        # Estimate routing if coordinates available
        eta_minutes = None
        distance_km = None
        try:
            maps = MapsService()
            routing = await maps.get_route_estimate(target_lat, target_lng)
            if routing:
                eta_minutes = routing.get("duration_minutes")
                distance_km = routing.get("distance_km")
        except Exception:
            pass  # Routing is best-effort

        assignment = DispatchAssignment(
            report_id=data.report_id,
            hotspot_id=data.hotspot_id,
            team_id=data.team_id,
            team_name=data.team_name,
            field_agent_id=data.field_agent_id,
            vehicle_type=data.vehicle_type,
            vehicle_id=data.vehicle_id,
            team_size=data.team_size,
            notes=data.notes,
            assigned_by_id=admin.id,
            estimated_arrival_minutes=eta_minutes,
            distance_km=distance_km,
        )
        self.db.add(assignment)
        await self.db.flush()
        return assignment

    async def update_status(
        self,
        dispatch_id: uuid.UUID,
        data: DispatchUpdateRequest,
        agent: User,
        before_photo_bytes: Optional[bytes] = None,
        after_photo_bytes: Optional[bytes] = None,
    ) -> DispatchAssignment:
        result = await self.db.execute(
            select(DispatchAssignment).where(DispatchAssignment.id == dispatch_id)
        )
        dispatch = result.scalar_one_or_none()
        if not dispatch:
            raise NotFoundException("DispatchAssignment", str(dispatch_id))

        now = datetime.now(timezone.utc)

        if data.status:
            dispatch.status = data.status
            if data.status == DispatchStatus.ACKNOWLEDGED:
                dispatch.acknowledged_at = now
            elif data.status == DispatchStatus.ARRIVED:
                dispatch.arrived_at = now
            elif data.status == DispatchStatus.COMPLETED:
                dispatch.completed_at = now
                # Close the linked report
                if dispatch.report_id:
                    rr = await self.db.execute(
                        select(Report).where(Report.id == dispatch.report_id)
                    )
                    report = rr.scalar_one_or_none()
                    if report:
                        report.status = ReportStatus.RESOLVED
                        report.resolved_at = now

        if data.estimated_arrival_minutes is not None:
            dispatch.estimated_arrival_minutes = data.estimated_arrival_minutes
        if data.notes:
            dispatch.notes = data.notes
        if data.completion_notes:
            dispatch.completion_notes = data.completion_notes

        if before_photo_bytes:
            key = await upload_dispatch_photo(before_photo_bytes, str(dispatch_id), "before")
            dispatch.before_photo_key = key
            dispatch.before_photo_url = get_photo_url(key)

        if after_photo_bytes:
            key = await upload_dispatch_photo(after_photo_bytes, str(dispatch_id), "after")
            dispatch.after_photo_key = key
            dispatch.after_photo_url = get_photo_url(key)

        return dispatch
