"""
CleanTrack AI — Notification ORM Model
Tracks FCM push and SMS notifications sent to users.
"""
import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class NotificationType(str, enum.Enum):
    REPORT_RECEIVED = "report_received"
    AI_PROCESSED = "ai_processed"
    REPORT_VERIFIED = "report_verified"
    DISPATCH_ASSIGNED = "dispatch_assigned"
    TEAM_EN_ROUTE = "team_en_route"
    REPORT_RESOLVED = "report_resolved"
    HOTSPOT_CREATED = "hotspot_created"
    SYSTEM_ALERT = "system_alert"


class NotificationChannel(str, enum.Enum):
    FCM = "fcm"    # Firebase Cloud Messaging (Android/web)
    APNS = "apns"  # Apple Push Notification Service
    SMS = "sms"    # Twilio SMS fallback


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type_enum"), nullable=False
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel_enum"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=True)  # Deep-link data

    # Linked entity (optional — for deep linking)
    report_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    dispatch_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Delivery status
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    send_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Provider message IDs
    fcm_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    twilio_sid: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="notifications", lazy="noload")

    def __repr__(self) -> str:
        return f"<Notification id={self.id} type={self.type} channel={self.channel}>"
