"""
CleanTrack AI — Analytics Router (v1)
GET /api/v1/analytics/summary   — Dashboard summary statistics
GET /api/v1/analytics/heatmap   — Heatmap data for map rendering
GET /api/v1/analytics/trends    — Weekly/monthly trend data
"""
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_municipal_admin
from app.models.dispatch import DispatchAssignment, DispatchStatus
from app.models.hotspot import Hotspot, HotspotSeverity
from app.models.report import Report, ReportStatus, WasteType
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsSummaryResponse, HeatmapPoint, HeatmapResponse,
    StatusBreakdown, WasteTypeBreakdown
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_summary(
    days: int = Query(30, ge=1, le=365, description="Look-back period in days"),
    current_user: User = Depends(require_municipal_admin),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard summary statistics for the given look-back period."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    # Total reports
    total_q = await db.execute(
        select(func.count(Report.id)).where(Report.created_at >= cutoff)
    )
    total_reports = total_q.scalar_one()

    # Resolved reports
    resolved_q = await db.execute(
        select(func.count(Report.id))
        .where(Report.created_at >= cutoff)
        .where(Report.status == ReportStatus.RESOLVED)
    )
    resolved_reports = resolved_q.scalar_one()

    # Avg resolution time (hours)
    res_time_q = await db.execute(
        select(
            func.avg(
                func.extract("epoch", Report.resolved_at - Report.created_at) / 3600
            )
        )
        .where(Report.created_at >= cutoff)
        .where(Report.status == ReportStatus.RESOLVED)
    )
    avg_res_hours = float(res_time_q.scalar_one() or 0)

    # Hotspot counts
    total_hs_q = await db.execute(select(func.count(Hotspot.id)))
    total_hotspots = total_hs_q.scalar_one()

    active_hs_q = await db.execute(
        select(func.count(Hotspot.id)).where(Hotspot.is_active == True)
    )
    active_hotspots = active_hs_q.scalar_one()

    critical_hs_q = await db.execute(
        select(func.count(Hotspot.id)).where(Hotspot.severity == HotspotSeverity.CRITICAL)
    )
    critical_hotspots = critical_hs_q.scalar_one()

    # Urgency breakdown
    high_q = await db.execute(
        select(func.count(Report.id))
        .where(Report.created_at >= cutoff)
        .where(Report.urgency_score >= 75)
    )
    med_q = await db.execute(
        select(func.count(Report.id))
        .where(Report.created_at >= cutoff)
        .where(Report.urgency_score.between(40, 74))
    )
    low_q = await db.execute(
        select(func.count(Report.id))
        .where(Report.created_at >= cutoff)
        .where(Report.urgency_score < 40)
    )

    # Waste type breakdown
    wt_q = await db.execute(
        select(Report.waste_type, func.count(Report.id).label("count"))
        .where(Report.created_at >= cutoff)
        .group_by(Report.waste_type)
    )
    wt_rows = wt_q.all()
    wt_total = sum(r.count for r in wt_rows)
    waste_breakdown = [
        WasteTypeBreakdown(
            waste_type=r.waste_type.value,
            count=r.count,
            percentage=round(r.count / wt_total * 100, 1) if wt_total else 0,
        )
        for r in wt_rows
    ]

    # Status breakdown
    st_q = await db.execute(
        select(Report.status, func.count(Report.id).label("count"))
        .where(Report.created_at >= cutoff)
        .group_by(Report.status)
    )
    status_breakdown = [
        StatusBreakdown(status=r.status.value, count=r.count)
        for r in st_q.all()
    ]

    # Dispatch stats
    disp_total_q = await db.execute(
        select(func.count(DispatchAssignment.id)).where(
            DispatchAssignment.assigned_at >= cutoff
        )
    )
    total_dispatches = disp_total_q.scalar_one()

    avg_eta_q = await db.execute(
        select(func.avg(DispatchAssignment.estimated_arrival_minutes)).where(
            DispatchAssignment.assigned_at >= cutoff
        )
    )
    avg_dispatch_response = float(avg_eta_q.scalar_one() or 0)

    return AnalyticsSummaryResponse(
        period_start=cutoff.date(),
        period_end=now.date(),
        total_reports=total_reports,
        resolved_reports=resolved_reports,
        resolution_rate=round(resolved_reports / total_reports * 100, 1) if total_reports else 0.0,
        avg_resolution_hours=round(avg_res_hours, 1),
        total_hotspots=total_hotspots,
        active_hotspots=active_hotspots,
        critical_hotspots=critical_hotspots,
        high_urgency_reports=high_q.scalar_one(),
        medium_urgency_reports=med_q.scalar_one(),
        low_urgency_reports=low_q.scalar_one(),
        waste_type_breakdown=waste_breakdown,
        status_breakdown=status_breakdown,
        total_dispatches=total_dispatches,
        avg_dispatch_response_minutes=round(avg_dispatch_response, 1),
    )


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_municipal_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Heatmap data — returns lat/lng/weight points for all recent reports.
    Weight is normalised urgency score.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(Report.latitude, Report.longitude, Report.urgency_score)
        .where(Report.created_at >= cutoff)
        .where(Report.status != ReportStatus.REJECTED)
        .where(Report.latitude.isnot(None))
    )
    rows = result.all()

    if not rows:
        return HeatmapResponse(points=[], max_weight=0.0, total_points=0)

    max_score = max(r.urgency_score or 0 for r in rows) or 1
    points = [
        HeatmapPoint(
            lat=r.latitude,
            lng=r.longitude,
            weight=round((r.urgency_score or 0) / max_score, 4),
        )
        for r in rows
    ]

    return HeatmapResponse(
        points=points,
        max_weight=1.0,
        total_points=len(points),
    )
