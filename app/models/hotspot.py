"""
CleanTrack AI — Hotspot ORM Model
Represents clusters of recurring waste reports in a geographic area.
"""
import enum
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Enum, Float, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class HotspotSeverity(str, enum.Enum):
    LOW = "low"         # 3-5 reports / 7 days
    MEDIUM = "medium"   # 6-10 reports / 7 days
    HIGH = "high"       # 11-20 reports / 7 days
    CRITICAL = "critical"  # 21+ reports / 7 days


class Hotspot(Base):
    __tablename__ = "hotspots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Centroid of the cluster
    centroid = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    centroid_lat: Mapped[float] = mapped_column(Float, nullable=False)
    centroid_lng: Mapped[float] = mapped_column(Float, nullable=False)

    # Convex hull / boundary polygon of all reports in cluster
    boundary = mapped_column(Geometry(geometry_type="POLYGON", srid=4326), nullable=True)

    # Human-readable location
    address: Mapped[str] = mapped_column(String(500), nullable=True)
    district: Mapped[str] = mapped_column(String(100), nullable=True)

    # Cluster statistics
    report_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    severity: Mapped[HotspotSeverity] = mapped_column(
        Enum(HotspotSeverity, name="hotspot_severity_enum", values_callable=lambda obj: [e.value for e in obj]),
        default=HotspotSeverity.LOW,
        nullable=False,
        index=True,
    )
    dominant_waste_type: Mapped[str] = mapped_column(String(50), nullable=True)
    avg_urgency_score: Mapped[float] = mapped_column(Float, nullable=True)

    # Radius of the cluster in metres
    radius_meters: Mapped[float] = mapped_column(Float, nullable=True)

    # DBSCAN cluster label (used internally during recompute)
    cluster_label: Mapped[int] = mapped_column(Integer, nullable=True)

    # Historical trend data (JSON for sparkline)
    trend_data: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)

    # Timestamps
    first_reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    last_recomputed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    reports = relationship("Report", back_populates="hotspot", lazy="noload")

    def __repr__(self) -> str:
        return f"<Hotspot id={self.id} severity={self.severity} reports={self.report_count}>"
