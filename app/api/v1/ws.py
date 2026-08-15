"""
CleanTrack AI — WebSocket Router (v1)

WS /ws/dashboard            — Live feed for municipal admin dashboard
WS /ws/report/{report_id}   — Citizen tracking for a specific report

Authentication: pass JWT token as query parameter ?token=<access_token>
"""
import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.config import get_settings
from app.core.redis_client import get_pubsub, CHANNEL_DASHBOARD, CHANNEL_REPORT_PREFIX

router = APIRouter(prefix="/ws", tags=["WebSocket"])
settings = get_settings()


def _verify_ws_token(token: str) -> dict:
    """Verify JWT from WebSocket query param."""
    from app.core.security import decode_token
    return decode_token(token)  # Raises HTTPException if invalid


@router.websocket("/dashboard")
async def dashboard_ws(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    Live dashboard WebSocket — streams report/dispatch events to admin clients.
    """
    try:
        payload = _verify_ws_token(token)
        role = payload.get("role")
        if role not in ("municipal_admin", "super_admin"):
            await websocket.close(code=4003)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    pubsub = await get_pubsub()
    await pubsub.subscribe(CHANNEL_DASHBOARD)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                await websocket.send_text(data)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await pubsub.unsubscribe(CHANNEL_DASHBOARD)
        await pubsub.aclose()


@router.websocket("/report/{report_id}")
async def report_tracking_ws(
    websocket: WebSocket,
    report_id: str,
    token: str = Query(...),
):
    """
    Per-report tracking WebSocket — streams status updates to the citizen reporter.
    """
    try:
        _verify_ws_token(token)
        UUID(report_id)  # Validate UUID format
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    channel = f"{CHANNEL_REPORT_PREFIX}{report_id}"
    pubsub = await get_pubsub()
    await pubsub.subscribe(channel)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
