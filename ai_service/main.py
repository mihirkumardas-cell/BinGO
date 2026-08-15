"""
CleanTrack AI — AI Microservice Entry Point
Internal FastAPI service running on port 8001.
Exposes:
  POST /analyze   — Full AI pipeline (classify + volume + urgency + dispatch rec)
  GET  /health    — Health check including model load status
"""
import time
from contextlib import asynccontextmanager
from typing import Optional

import structlog
from fastapi import FastAPI, HTTPException

from ai_service.classifier import WasteClassifier
from ai_service.dispatch_recommender import recommend_dispatch
from ai_service.schemas import AnalyzeRequest, AnalyzeResponse, BoundingBox, HealthResponse
from ai_service.urgency_scorer import compute_urgency
from ai_service.volume_estimator import estimate_volume

logger = structlog.get_logger()

# Global model instance (loaded once at startup)
_classifier: Optional[WasteClassifier] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model at startup."""
    global _classifier
    import os
    model_path = os.getenv("YOLO_MODEL_PATH", "./weights/cleantrack_yolov8n.pt")
    _classifier = WasteClassifier(model_path=model_path)
    logger.info("ai_service_ready", model_version=_classifier.model_version)
    yield
    logger.info("ai_service_shutting_down")


app = FastAPI(
    title="CleanTrack AI — Computer Vision Microservice",
    description=(
        "Internal CV pipeline for waste classification, volume estimation, "
        "urgency scoring, and dispatch recommendation.\n\n"
        "**Dataset**: [Kaggle Garbage Classification](https://www.kaggle.com/datasets/asdasdasasdas/garbage-classification) "
        "+ [TACO](http://tacoDataset.org/)\n"
        "**Model**: YOLOv8n fine-tuned on TACO bounding boxes"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy" if (_classifier and _classifier.is_loaded) else "degraded",
        model_loaded=_classifier is not None and _classifier.is_loaded,
        model_path=_classifier.model_path if _classifier else "not_loaded",
    )


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """
    Full AI pipeline:
    1. Download photo from S3
    2. Run YOLOv8 detection
    3. Estimate volume from bounding box
    4. Score urgency
    5. Recommend vehicle / team
    """
    if not _classifier or not _classifier.is_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded")

    start_ms = int(time.time() * 1000)

    # 1. Download photo from MinIO/S3
    photo_bytes = await _fetch_photo(request.photo_key)

    # 2. Detect waste
    waste_type, confidence, bbox_dict = _classifier.detect(photo_bytes)

    # 3. Volume estimation
    volume_m3 = estimate_volume(waste_type, bbox_dict)

    # 4. Urgency score
    from datetime import datetime, timezone
    urgency = compute_urgency(
        waste_type=waste_type,
        volume_m3=volume_m3,
        reported_at=datetime.now(timezone.utc),
    )

    # 5. Dispatch recommendation
    vehicle, team_size = recommend_dispatch(waste_type, volume_m3)

    elapsed_ms = int(time.time() * 1000) - start_ms

    logger.info(
        "analysis_complete",
        waste_type=waste_type,
        confidence=round(confidence, 3),
        volume=volume_m3,
        urgency=urgency,
        vehicle=vehicle,
        ms=elapsed_ms,
    )

    bbox_model = None
    if bbox_dict:
        bbox_model = BoundingBox(**bbox_dict)

    return AnalyzeResponse(
        waste_type=waste_type,
        confidence=round(confidence, 4),
        bounding_box=bbox_model,
        volume_estimate_m3=volume_m3,
        urgency_score=urgency,
        recommended_vehicle=vehicle,
        recommended_team_size=team_size,
        model_version=_classifier.model_version,
        processing_ms=elapsed_ms,
    )


async def _fetch_photo(photo_key: str) -> bytes:
    """Download photo bytes from S3-compatible storage."""
    import os
    import boto3
    from botocore.config import Config

    s3 = boto3.client(
        "s3",
        endpoint_url=os.getenv("STORAGE_ENDPOINT_URL", "http://minio:9000"),
        aws_access_key_id=os.getenv("STORAGE_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.getenv("STORAGE_SECRET_KEY", "minioadmin"),
        region_name=os.getenv("STORAGE_REGION", "us-east-1"),
        config=Config(signature_version="s3v4"),
    )

    bucket = os.getenv("STORAGE_BUCKET_PHOTOS", "cleantrack-photos")
    resp = s3.get_object(Bucket=bucket, Key=photo_key)
    return resp["Body"].read()
