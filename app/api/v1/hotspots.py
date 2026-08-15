"""
CleanTrack AI — Hotspots Router (v1)
GET /api/v1/hotspots          — List active hotspots (with bbox filter)
GET /api/v1/hotspots/{id}     — Get hotspot detail
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.hotspot import HotspotSeverity
from app.models.user import User
from app.schemas.hotspot import HotspotListResponse, HotspotResponse
from app.services.hotspot_service import HotspotService

router = APIRouter(prefix="/hotspots", tags=["Hotspots"])


@router.get("", response_model=HotspotListResponse)
async def list_hotspots(
    min_lat: Optional[float] = Query(None, ge=-90, le=90),
    min_lng: Optional[float] = Query(None, ge=-180, le=180),
    max_lat: Optional[float] = Query(None, ge=-90, le=90),
    max_lng: Optional[float] = Query(None, ge=-180, le=180),
    severity: Optional[HotspotSeverity] = None,
    is_active: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List hotspots. If bbox params provided, filters to map viewport.
    Used by the municipal dashboard map view.
    """
    service = HotspotService(db)

    if all(v is not None for v in [min_lat, min_lng, max_lat, max_lng]):
        hotspots = await service.get_hotspots_in_bbox(
            min_lat, min_lng, max_lat, max_lng, severity=severity
        )
    else:
        from sqlalchemy import select
        from app.models.hotspot import Hotspot
        query = select(Hotspot).where(Hotspot.is_active == is_active)
        if severity:
            query = query.where(Hotspot.severity == severity)
        result = await db.execute(query)
        hotspots = result.scalars().all()

    return HotspotListResponse(items=hotspots, total=len(hotspots))


@router.get("/{hotspot_id}", response_model=HotspotResponse)
async def get_hotspot(
    hotspot_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detail for a specific hotspot including linked reports."""
    from sqlalchemy import select
    from app.models.hotspot import Hotspot
    from app.core.exceptions import NotFoundException

    result = await db.execute(select(Hotspot).where(Hotspot.id == hotspot_id))
    hotspot = result.scalar_one_or_none()
    if not hotspot:
        raise NotFoundException("Hotspot", str(hotspot_id))
    return hotspot
