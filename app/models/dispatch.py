"""
CleanTrack AI — Dispatch Assignment ORM Model
Links a sanitation team to a report or hotspot, with before/after photo proof.
"""
import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class VehicleType(str, enum.Enum):
    COMPACT_VAN = "compact_van"           # Small loads, narrow streets
    COLLECTION_TRUCK = "collection_truck" # Standard municipal truck
    HAZMAT_UNIT = "hazmat_unit"           # Hazardous waste
    STREET_SWEEPER = "street_sweeper"     # Scattered litter
    BULK_LOADER = "bulk_loader"           # Large volume / construction debris
    MOTORCYCLE = "motorcycle"             # Rapid assessment only


class DispatchStatus(str, enum.Enum):
    ASSIGNED = "assigned"
    ACKNOWLEDGED = "acknowledged"   # Field agent confirmed
    EN_ROUTE = "en_route"
    ARRIVED = "arrived"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DispatchAssignment(Base):
    __tablename__ = "dispatch_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Target — exactly one of report_id or hotspot_id must be set
    report_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=True, index=True
    )
    hotspot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hotspots.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Team info
    team_id: Mapped[str] = mapped_column(String(100), nullable=False)
    team_name: Mapped[str] = mapped_column(String(255), nullable=True)
    field_agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    vehicle_type: Mapped[VehicleType] = mapped_column(
        Enum(VehicleType, name="vehicle_type_enum"), nullable=False
    )
    vehicle_id: Mapped[str] = mapped_column(String(100), nullable=True)
    team_size: Mapped[int] = mapped_column(Integer, default=2)

    # Status
    status: Mapped[DispatchStatus] = mapped_column(
        Enum(DispatchStatus, name="dispatch_status_enum"),
        default=DispatchStatus.ASSIGNED,
        nullable=False,
        index=True,
    )

    # Routing
    estimated_arrival_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    route_polyline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # encoded polyline
    distance_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Photo proof (before/after)
    before_photo_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    before_photo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    after_photo_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    after_photo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completion_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Who assigned
    assigned_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    arrived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    report = relationship("Report", back_populates="dispatch_assignment", lazy="noload")
    field_agent = relationship("User", foreign_keys=[field_agent_id], lazy="noload")
    assigned_by = relationship("User", foreign_keys=[assigned_by_id], lazy="noload")

    def __repr__(self) -> str:
        return f"<Dispatch id={self.id} status={self.status} team={self.team_id}>"
