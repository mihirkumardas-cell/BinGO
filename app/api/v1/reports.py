"""
CleanTrack AI — Reports Router (v1)

POST   /api/v1/reports                    — Submit a new waste report (multipart)
GET    /api/v1/reports                    — List reports (with filters)
GET    /api/v1/reports/{id}               — Get report detail
PATCH  /api/v1/reports/{id}              — Update report (reporter)
POST   /api/v1/reports/{id}/verify        — Admin verify / override AI output
POST   /api/v1/reports/{id}/close         — Field agent close with after-photo
GET    /api/v1/reports/{id}/nearby        — Find nearby reports
POST   /api/v1/reports/{id}/presign       — Get presigned upload URL
"""
import uuid
from typing import Optional

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException,
    Query, UploadFile, status
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_citizen, require_field_agent, require_municipal_admin
from app.core.storage import upload_report_photo, get_photo_url
from app.models.report import ReportStatus, WasteType
from app.models.user import User
from app.schemas.report import (
    ReportCloseRequest, ReportCreateRequest,
    ReportListResponse, ReportResponse, ReportVerifyRequest
)
from app.services.report_service import ReportService
from app.workers.photo_processor import enqueue_photo_processing

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    latitude: float = Form(..., ge=-90, le=90),
    longitude: float = Form(..., ge=-180, le=180),
    description: Optional[str] = Form(None),
    photo: UploadFile = File(...),
    current_user: User = Depends(require_citizen),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a new waste report with photo.
    The photo is immediately uploaded to S3; AI processing is queued asynchronously.
    """
    # Validate file type
    if photo.content_type not in ("image/jpeg", "image/jpg", "image/png", "image/webp"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Photo must be JPEG, PNG, or WebP",
        )

    # Read photo bytes (max 20 MB guard)
    photo_bytes = await photo.read()
    if len(photo_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Photo too large (max 20 MB)")

    # Create report record first (to get the ID)
    from app.schemas.report import ReportCreateRequest
    data = ReportCreateRequest(latitude=latitude, longitude=longitude, description=description)
    service = ReportService(db)
    report = await service.create(data, current_user)

    # Upload photos to S3
    photo_key, thumb_key = await upload_report_photo(
        photo_bytes, str(report.id), photo.filename or "photo.jpg"
    )
    report.photo_key = photo_key
    report.photo_url = get_photo_url(photo_key)
    report.thumbnail_key = thumb_key
    report.thumbnail_url = get_photo_url(thumb_key, bucket="cleantrack-thumbs")

    # Queue async AI processing job
    await enqueue_photo_processing(
        report_id=str(report.id),
        photo_key=photo_key,
        latitude=latitude,
        longitude=longitude,
    )

    return report


@router.get("", response_model=ReportListResponse)
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[ReportStatus] = None,
    waste_type: Optional[WasteType] = None,
    min_urgency: Optional[int] = Query(None, ge=0, le=100),
    min_lat: Optional[float] = None,
    min_lng: Optional[float] = None,
    max_lat: Optional[float] = None,
    max_lng: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List reports with optional filters.
    Citizens see only their own reports. Admins/agents see all.
    """
    service = ReportService(db)

    bbox = None
    if all(v is not None for v in [min_lat, min_lng, max_lat, max_lng]):
        bbox = (min_lat, min_lng, max_lat, max_lng)

    from app.models.user import UserRole
    reporter_id = None
    if current_user.role == UserRole.CITIZEN:
        reporter_id = current_user.id

    return await service.list_reports(
        page=page,
        page_size=page_size,
        status=status,
        waste_type=waste_type,
        reporter_id=reporter_id,
        min_urgency=min_urgency,
        bbox=bbox,
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific report by ID."""
    service = ReportService(db)
    return await service.get_by_id(report_id)


@router.post("/{report_id}/verify", response_model=ReportResponse)
async def verify_report(
    report_id: uuid.UUID,
    data: ReportVerifyRequest,
    current_user: User = Depends(require_municipal_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Municipal admin verifies or overrides the AI output.
    Can correct waste type, volume, urgency score, or reject the report.
    """
    service = ReportService(db)
    report = await service.verify(report_id, data, current_user)

    # Publish WebSocket event
    from app.core.redis_client import publish_event, CHANNEL_DASHBOARD
    await publish_event(CHANNEL_DASHBOARD, {
        "event": "report_verified",
        "report_id": str(report.id),
        "status": report.status.value,
    })

    return report


@router.post("/{report_id}/close", response_model=ReportResponse)
async def close_report(
    report_id: uuid.UUID,
    completion_notes: Optional[str] = Form(None),
    after_photo: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_field_agent),
    db: AsyncSession = Depends(get_db),
):
    """Field agent closes report with optional after-photo proof."""
    after_bytes = None
    if after_photo:
        after_bytes = await after_photo.read()

    service = ReportService(db)
    report = await service.close(
        report_id, current_user, after_bytes, completion_notes
    )

    # Notify reporter
    from app.services.notification_service import NotificationService
    from app.models.notification import NotificationType
    from sqlalchemy import select
    from app.models.user import User as UserModel
    if report.reporter_id:
        result = await db.execute(select(UserModel).where(UserModel.id == report.reporter_id))
        reporter = result.scalar_one_or_none()
        if reporter:
            notif_svc = NotificationService(db)
            await notif_svc.send_push(
                user=reporter,
                notif_type=NotificationType.REPORT_RESOLVED,
                title="✅ Issue Resolved!",
                body="Your waste report has been addressed by the sanitation team.",
                payload={"report_id": str(report_id)},
                report_id=report_id,
            )

    return report


@router.get("/{report_id}/nearby", response_model=list)
async def get_nearby_reports(
    report_id: uuid.UUID,
    radius_meters: float = Query(500, ge=50, le=5000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Find other reports near a given report."""
    service = ReportService(db)
    report = await service.get_by_id(report_id)
    nearby = await service.get_nearby_reports(
        report.latitude, report.longitude, radius_meters
    )
    return [ReportResponse.model_validate(r) for r in nearby if r.id != report_id]
