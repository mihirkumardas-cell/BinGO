"""
CleanTrack AI — Hotspot Pydantic Schemas
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.models.hotspot import HotspotSeverity


class HotspotResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    centroid_lat: float
    centroid_lng: float
    address: Optional[str]
    district: Optional[str]
    report_count: int
    severity: HotspotSeverity
    dominant_waste_type: Optional[str]
    avg_urgency_score: Optional[float]
    radius_meters: Optional[float]
    trend_data: Optional[Dict[str, Any]]
    is_active: bool
    first_reported_at: Optional[datetime]
    last_reported_at: Optional[datetime]
    last_recomputed_at: datetime
    resolved_at: Optional[datetime]


class HotspotListResponse(BaseModel):
    items: List[HotspotResponse]
    total: int


class HotspotBoundingBoxQuery(BaseModel):
    """Query hotspots within a map bounding box."""
    min_lat: float
    min_lng: float
    max_lat: float
    max_lng: float
    severity: Optional[HotspotSeverity] = None
    is_active: Optional[bool] = True
