"""
CleanTrack AI — AI Microservice Schemas
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    photo_key: str          # S3 key of the photo to analyze
    latitude: float
    longitude: float


class BoundingBox(BaseModel):
    x: float                # Top-left x (0-1 normalised)
    y: float                # Top-left y (0-1 normalised)
    width: float            # Box width (0-1 normalised)
    height: float           # Box height (0-1 normalised)
    confidence: float


class AnalyzeResponse(BaseModel):
    waste_type: str
    confidence: float       # 0.0 – 1.0
    bounding_box: Optional[BoundingBox]
    volume_estimate_m3: float
    urgency_score: int      # 0 – 100
    recommended_vehicle: str
    recommended_team_size: int
    model_version: str
    processing_ms: int
    raw_detections: Optional[list] = None


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_path: str
    version: str = "1.0.0"
