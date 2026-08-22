"""
CleanTrack AI — User ORM Model
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    CITIZEN = "citizen"
    FIELD_AGENT = "field_agent"
    MUNICIPAL_ADMIN = "municipal_admin"
    SUPER_ADMIN = "super_admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=UserRole.CITIZEN,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Device tokens for push notifications
    fcm_token: Mapped[str] = mapped_column(Text, nullable=True)  # Firebase Cloud Messaging
    apns_token: Mapped[str] = mapped_column(Text, nullable=True)  # Apple Push

    # Municipal staff assignment (which zone/district they cover)
    assigned_zone: Mapped[str] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    reports = relationship(
        "Report",
        foreign_keys="[Report.reporter_id]",
        back_populates="reporter",
        lazy="noload",
    )
    notifications = relationship("Notification", back_populates="user", lazy="noload")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
