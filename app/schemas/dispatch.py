"""
CleanTrack AI — Dispatch Pydantic Schemas
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.dispatch import DispatchStatus, VehicleType


class DispatchAssignRequest(BaseModel):
    report_id: Optional[uuid.UUID] = None
    hotspot_id: Optional[uuid.UUID] = None
    team_id: str = Field(..., min_length=1, max_length=100)
    team_name: Optional[str] = Field(None, max_length=255)
    field_agent_id: Optional[uuid.UUID] = None
    vehicle_type: VehicleType
    vehicle_id: Optional[str] = Field(None, max_length=100)
    team_size: int = Field(2, ge=1, le=20)
    notes: Optional[str] = Field(None, max_length=1000)


class DispatchUpdateRequest(BaseModel):
    status: Optional[DispatchStatus] = None
    estimated_arrival_minutes: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=1000)
    completion_notes: Optional[str] = Field(None, max_length=1000)
    # before/after photos uploaded as multipart files


class DispatchResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    report_id: Optional[uuid.UUID]
    hotspot_id: Optional[uuid.UUID]
    team_id: str
    team_name: Optional[str]
    field_agent_id: Optional[uuid.UUID]
    vehicle_type: VehicleType
    vehicle_id: Optional[str]
    team_size: int
    status: DispatchStatus
    estimated_arrival_minutes: Optional[int]
    distance_km: Optional[float]
    before_photo_url: Optional[str]
    after_photo_url: Optional[str]
    notes: Optional[str]
    completion_notes: Optional[str]
    assigned_at: datetime
    acknowledged_at: Optional[datetime]
    arrived_at: Optional[datetime]
    completed_at: Optional[datetime]
