"""
CleanTrack AI — Report Pydantic Schemas
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.report import ReportStatus, WasteType
from app.models.dispatch import VehicleType


class ReportCreateRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    description: Optional[str] = Field(None, max_length=1000)
    # photo is uploaded as multipart file — not in this JSON body


class AIAnalysisResult(BaseModel):
    waste_type: WasteType
    confidence: float
    bounding_box: Optional[Dict[str, float]]
    volume_estimate_m3: float
    urgency_score: int
    is_duplicate: bool
    duplicate_of_id: Optional[uuid.UUID]
    recommended_vehicle: VehicleType
    recommended_team_size: int
    raw_output: Optional[Dict[str, Any]]


class ReportResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    reporter_id: Optional[uuid.UUID]
    latitude: float
    longitude: float
    address: Optional[str]
    city: Optional[str]
    district: Optional[str]
    waste_type: WasteType
    ai_confidence: Optional[float]
    volume_estimate_m3: Optional[float]
    urgency_score: Optional[int]
    recurrence_count: int
    photo_url: Optional[str]
    thumbnail_url: Optional[str]
    status: ReportStatus
    is_duplicate: bool
    duplicate_of_id: Optional[uuid.UUID]
    hotspot_id: Optional[uuid.UUID]
    recommended_vehicle: Optional[str]
    recommended_team_size: Optional[int]
    description: Optional[str]
    admin_notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]


class ReportListResponse(BaseModel):
    items: List[ReportResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class ReportVerifyRequest(BaseModel):
    """Municipal admin confirms or overrides the AI output."""
    waste_type: Optional[WasteType] = None
    volume_estimate_m3: Optional[float] = None
    urgency_score: Optional[int] = Field(None, ge=0, le=100)
    admin_notes: Optional[str] = Field(None, max_length=1000)
    is_rejected: bool = False
    rejection_reason: Optional[str] = None


class ReportCloseRequest(BaseModel):
    """Field agent closes report with after-photo proof."""
    completion_notes: Optional[str] = Field(None, max_length=1000)
    # after_photo uploaded as multipart file


class ReportUpdateRequest(BaseModel):
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[ReportStatus] = None
