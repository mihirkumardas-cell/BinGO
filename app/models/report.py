"""
CleanTrack AI — Report ORM Model (core entity)
Uses PostGIS geometry for GPS location.
"""
import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WasteType(str, enum.Enum):
    CARDBOARD = "cardboard"
    GLASS = "glass"
    METAL = "metal"
    PAPER = "paper"
    PLASTIC = "plastic"
    ORGANIC = "organic"
    HAZARDOUS = "hazardous"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class ReportStatus(str, enum.Enum):
    PENDING_AI = "pending_ai"          # Uploaded, queued for CV processing
    AI_PROCESSED = "ai_processed"     # CV done, awaiting human verify
    VERIFIED = "verified"             # Admin confirmed AI output
    DUPLICATE = "duplicate"           # Merged with existing report
    DISPATCHED = "dispatched"         # Team assigned
    IN_PROGRESS = "in_progress"       # Field agent on-site
    RESOLVED = "resolved"             # Closed with after-photo
    REJECTED = "rejected"             # Admin rejected (false report)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Reporter
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # ── Location (PostGIS) ────────────────────────────────────────
    location = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=False
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=True)  # Reverse geocoded
    city: Mapped[str] = mapped_column(String(100), nullable=True)
    district: Mapped[str] = mapped_column(String(100), nullable=True)

    # ── AI Classification ─────────────────────────────────────────
    waste_type: Mapped[WasteType] = mapped_column(
        Enum(WasteType, name="waste_type_enum", values_callable=lambda obj: [e.value for e in obj]),
        default=WasteType.UNKNOWN,
        nullable=False,
    )
    ai_confidence: Mapped[float] = mapped_column(Float, nullable=True)  # 0.0 – 1.0
    ai_bounding_box: Mapped[dict] = mapped_column(JSON, nullable=True)  # {x,y,w,h}
    volume_estimate_m3: Mapped[float] = mapped_column(Float, nullable=True)  # cubic metres
    ai_raw_output: Mapped[dict] = mapped_column(JSON, nullable=True)  # Full YOLO output

    # ── Urgency & Scoring ─────────────────────────────────────────
    urgency_score: Mapped[int] = mapped_column(Integer, nullable=True)   # 0–100
    recurrence_count: Mapped[int] = mapped_column(Integer, default=1)    # How many times this hotspot has been reported

    # ── Photos ───────────────────────────────────────────────────
    photo_key: Mapped[str] = mapped_column(String(500), nullable=True)   # S3 key
    photo_url: Mapped[str] = mapped_column(Text, nullable=True)          # Public URL
    thumbnail_key: Mapped[str] = mapped_column(String(500), nullable=True)
    thumbnail_url: Mapped[str] = mapped_column(Text, nullable=True)

    # ── Status & Deduplication ────────────────────────────────────
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status_enum", values_callable=lambda obj: [e.value for e in obj]),
        default=ReportStatus.PENDING_AI,
        nullable=False,
        index=True,
    )
    duplicate_of_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id", ondelete="SET NULL"), nullable=True
    )
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Hotspot linkage ───────────────────────────────────────────
    hotspot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hotspots.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # ── Dispatch recommendation ───────────────────────────────────
    recommended_vehicle: Mapped[str] = mapped_column(String(50), nullable=True)
    recommended_team_size: Mapped[int] = mapped_column(Integer, nullable=True)

    # ── Metadata ──────────────────────────────────────────────────
    description: Mapped[str] = mapped_column(Text, nullable=True)  # Citizen notes
    device_info: Mapped[dict] = mapped_column(JSON, nullable=True)  # OS, app version
    ip_address: Mapped[str] = mapped_column(String(50), nullable=True)

    # ── Admin overrides ───────────────────────────────────────────
    verified_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    admin_notes: Mapped[str] = mapped_column(Text, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────────
    reporter = relationship("User", foreign_keys=[reporter_id], back_populates="reports", lazy="noload")
    hotspot = relationship("Hotspot", back_populates="reports", lazy="noload")
    dispatch_assignment = relationship("DispatchAssignment", back_populates="report", lazy="noload", uselist=False)

    def __repr__(self) -> str:
        return f"<Report id={self.id} type={self.waste_type} status={self.status}>"
