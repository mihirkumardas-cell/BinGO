"""
CleanTrack AI — Analytics Pydantic Schemas
"""
from datetime import date
from typing import Any, Dict, List

from pydantic import BaseModel


class WasteTypeBreakdown(BaseModel):
    waste_type: str
    count: int
    percentage: float


class StatusBreakdown(BaseModel):
    status: str
    count: int


class AnalyticsSummaryResponse(BaseModel):
    period_start: date
    period_end: date

    # Volume metrics
    total_reports: int
    resolved_reports: int
    resolution_rate: float
    avg_resolution_hours: float

    # AI metrics
    total_hotspots: int
    active_hotspots: int
    critical_hotspots: int

    # Urgency distribution
    high_urgency_reports: int   # score >= 75
    medium_urgency_reports: int  # score 40-74
    low_urgency_reports: int     # score < 40

    # Breakdowns
    waste_type_breakdown: List[WasteTypeBreakdown]
    status_breakdown: List[StatusBreakdown]

    # Dispatch
    total_dispatches: int
    avg_dispatch_response_minutes: float


class HeatmapPoint(BaseModel):
    lat: float
    lng: float
    weight: float  # urgency score normalised 0-1


class HeatmapResponse(BaseModel):
    points: List[HeatmapPoint]
    max_weight: float
    total_points: int
