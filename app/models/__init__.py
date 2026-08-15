"""CleanTrack AI ORM Models — package init."""
from app.models.user import User, UserRole
from app.models.report import Report, ReportStatus, WasteType
from app.models.hotspot import Hotspot, HotspotSeverity
from app.models.dispatch import DispatchAssignment, DispatchStatus, VehicleType
from app.models.notification import Notification, NotificationType

__all__ = [
    "User", "UserRole",
    "Report", "ReportStatus", "WasteType",
    "Hotspot", "HotspotSeverity",
    "DispatchAssignment", "DispatchStatus", "VehicleType",
    "Notification", "NotificationType",
]
