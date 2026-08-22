"""
CleanTrack AI — Dispatch Router (v1)
POST  /api/v1/dispatch/assign          — Assign team to report/hotspot (admin)
PATCH /api/v1/dispatch/{id}/status     — Update dispatch status (field agent)
GET   /api/v1/dispatch/{id}            — Get dispatch detail
GET   /api/v1/dispatch                 — List dispatches (admin)
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.core.security import get_current_user, require_field_agent, require_municipal_admin
from app.models.dispatch import DispatchAssignment, DispatchStatus
from app.models.user import User
from app.schemas.dispatch import DispatchAssignRequest, DispatchResponse, DispatchUpdateRequest
from app.services.dispatch_service import DispatchService

router = APIRouter(prefix="/dispatch", tags=["Dispatch"])


@router.post("/assign", response_model=DispatchResponse, status_code=status.HTTP_201_CREATED)
async def assign_dispatch(
    data: DispatchAssignRequest,
    current_user: User = Depends(require_municipal_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Assign a sanitation team to a report or hotspot.
    Triggers push notification to the field agent.
    """
    service = DispatchService(db)
    assignment = await service.assign(data, current_user)

    # Notify the field agent if specified
    if data.field_agent_id:
        result = await db.execute(
            select(User).where(User.id == data.field_agent_id)
        )
        agent = result.scalar_one_or_none()
        if agent:
            from app.services.notification_service import NotificationService
            from app.models.notification import NotificationType
            notif = NotificationService(db)
            await notif.send_push(
                user=agent,
                notif_type=NotificationType.DISPATCH_ASSIGNED,
                title="🚛 New Assignment",
                body=f"You have been assigned to dispatch {assignment.id}.",
                payload={"dispatch_id": str(assignment.id)},
                dispatch_id=assignment.id,
            )

    # Broadcast to dashboard WebSocket
    from app.core.redis_client import publish_event, CHANNEL_DASHBOARD
    await publish_event(CHANNEL_DASHBOARD, {
        "event": "dispatch_created",
        "dispatch_id": str(assignment.id),
        "team_id": assignment.team_id,
    })

    return assignment


@router.patch("/{dispatch_id}/status", response_model=DispatchResponse)
async def update_dispatch_status(
    dispatch_id: uuid.UUID,
    status: Optional[DispatchStatus] = Form(None),
    estimated_arrival_minutes: Optional[int] = Form(None),
    notes: Optional[str] = Form(None),
    completion_notes: Optional[str] = Form(None),
    before_photo: Optional[UploadFile] = File(None),
    after_photo: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_field_agent),
    db: AsyncSession = Depends(get_db),
):
    """Update dispatch status and optionally upload before/after photos."""
    before_bytes = await before_photo.read() if before_photo else None
    after_bytes = await after_photo.read() if after_photo else None

    data = DispatchUpdateRequest(
        status=status,
        estimated_arrival_minutes=estimated_arrival_minutes,
        notes=notes,
        completion_notes=completion_notes,
    )

    service = DispatchService(db)
    assignment = await service.update_status(
        dispatch_id, data, current_user, before_bytes, after_bytes
    )

    # Broadcast status update to dashboard and report tracking channel
    from app.core.redis_client import publish_event, CHANNEL_DASHBOARD, CHANNEL_REPORT_PREFIX
    event = {
        "event": "dispatch_status_updated",
        "dispatch_id": str(dispatch_id),
        "status": assignment.status.value,
    }
    await publish_event(CHANNEL_DASHBOARD, event)
    if assignment.report_id:
        await publish_event(f"{CHANNEL_REPORT_PREFIX}{assignment.report_id}", event)

    return assignment


@router.get("/{dispatch_id}", response_model=DispatchResponse)
async def get_dispatch(
    dispatch_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DispatchAssignment).where(DispatchAssignment.id == dispatch_id)
    )
    dispatch = result.scalar_one_or_none()
    if not dispatch:
        raise NotFoundException("DispatchAssignment", str(dispatch_id))
    return dispatch


@router.get("", response_model=list)
async def list_dispatches(
    dispatch_status: Optional[DispatchStatus] = Query(None),
    team_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_field_agent),
    db: AsyncSession = Depends(get_db),
):
    query = select(DispatchAssignment).order_by(DispatchAssignment.assigned_at.desc())
    if dispatch_status:
        query = query.where(DispatchAssignment.status == dispatch_status)
    if team_id:
        query = query.where(DispatchAssignment.team_id == team_id)
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    dispatches = result.scalars().all()
    return [DispatchResponse.model_validate(d) for d in dispatches]
