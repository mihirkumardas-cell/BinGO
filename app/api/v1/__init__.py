"""CleanTrack AI — API v1 package."""
from fastapi import APIRouter

from app.api.v1 import auth, reports, hotspots, dispatch, analytics, ws

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth.router)
api_v1_router.include_router(reports.router)
api_v1_router.include_router(hotspots.router)
api_v1_router.include_router(dispatch.router)
api_v1_router.include_router(analytics.router)
api_v1_router.include_router(ws.router)
