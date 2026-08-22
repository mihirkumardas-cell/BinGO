"""
Initial migration — creates all CleanTrack tables with PostGIS geometry.
"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("citizen","field_agent","municipal_admin","super_admin", name="user_role_enum"), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("is_verified", sa.Boolean(), default=False),
        sa.Column("fcm_token", sa.Text(), nullable=True),
        sa.Column("apns_token", sa.Text(), nullable=True),
        sa.Column("assigned_zone", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ── hotspots ──────────────────────────────────────────────────────────────
    op.create_table(
        "hotspots",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("centroid", geoalchemy2.Geometry("POINT", srid=4326), nullable=False),
        sa.Column("centroid_lat", sa.Float(), nullable=False),
        sa.Column("centroid_lng", sa.Float(), nullable=False),
        sa.Column("boundary", geoalchemy2.Geometry("POLYGON", srid=4326), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("district", sa.String(100), nullable=True),
        sa.Column("report_count", sa.Integer(), default=0),
        sa.Column("severity", sa.Enum("low","medium","high","critical", name="hotspot_severity_enum"), nullable=False),
        sa.Column("dominant_waste_type", sa.String(50), nullable=True),
        sa.Column("avg_urgency_score", sa.Float(), nullable=True),
        sa.Column("radius_meters", sa.Float(), nullable=True),
        sa.Column("cluster_label", sa.Integer(), nullable=True),
        sa.Column("trend_data", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("first_reported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_recomputed_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── reports ───────────────────────────────────────────────────────────────
    op.create_table(
        "reports",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reporter_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("location", geoalchemy2.Geometry("POINT", srid=4326), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("district", sa.String(100), nullable=True),
        sa.Column("waste_type", sa.Enum("cardboard","glass","metal","paper","plastic",
                  "organic","hazardous","mixed","unknown", name="waste_type_enum"), nullable=False),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("ai_bounding_box", sa.JSON(), nullable=True),
        sa.Column("volume_estimate_m3", sa.Float(), nullable=True),
        sa.Column("ai_raw_output", sa.JSON(), nullable=True),
        sa.Column("urgency_score", sa.Integer(), nullable=True),
        sa.Column("recurrence_count", sa.Integer(), default=1),
        sa.Column("photo_key", sa.String(500), nullable=True),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.Column("thumbnail_key", sa.String(500), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("pending_ai","ai_processed","verified","duplicate",
                  "dispatched","in_progress","resolved","rejected", name="report_status_enum"), nullable=False),
        sa.Column("duplicate_of_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("reports.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_duplicate", sa.Boolean(), default=False),
        sa.Column("hotspot_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("hotspots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recommended_vehicle", sa.String(50), nullable=True),
        sa.Column("recommended_team_size", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("device_info", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("verified_by_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    # PostGIS spatial index on location
    op.execute("CREATE INDEX ix_reports_location ON reports USING GIST(location)")
    op.create_index("ix_reports_status", "reports", ["status"])
    op.create_index("ix_reports_created_at", "reports", ["created_at"])

    # PostGIS index on hotspot centroid
    op.execute("CREATE INDEX ix_hotspots_centroid ON hotspots USING GIST(centroid)")

    # ── dispatch_assignments ──────────────────────────────────────────────────
    op.create_table(
        "dispatch_assignments",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("reports.id", ondelete="CASCADE"), nullable=True),
        sa.Column("hotspot_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("hotspots.id", ondelete="CASCADE"), nullable=True),
        sa.Column("team_id", sa.String(100), nullable=False),
        sa.Column("team_name", sa.String(255), nullable=True),
        sa.Column("field_agent_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("vehicle_type", sa.Enum("compact_van","collection_truck","hazmat_unit",
                  "street_sweeper","bulk_loader","motorcycle", name="vehicle_type_enum"), nullable=False),
        sa.Column("vehicle_id", sa.String(100), nullable=True),
        sa.Column("team_size", sa.Integer(), default=2),
        sa.Column("status", sa.Enum("assigned","acknowledged","en_route","arrived",
                  "in_progress","completed","cancelled", name="dispatch_status_enum"), nullable=False),
        sa.Column("estimated_arrival_minutes", sa.Integer(), nullable=True),
        sa.Column("route_polyline", sa.Text(), nullable=True),
        sa.Column("distance_km", sa.Float(), nullable=True),
        sa.Column("before_photo_key", sa.String(500), nullable=True),
        sa.Column("before_photo_url", sa.Text(), nullable=True),
        sa.Column("after_photo_key", sa.String(500), nullable=True),
        sa.Column("after_photo_url", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("completion_notes", sa.Text(), nullable=True),
        sa.Column("assigned_by_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True)),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("arrived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── notifications ─────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.Enum("report_received","ai_processed","report_verified",
                  "dispatch_assigned","team_en_route","report_resolved",
                  "hotspot_created","system_alert", name="notification_type_enum"), nullable=False),
        sa.Column("channel", sa.Enum("fcm","apns","sms", name="notification_channel_enum"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("report_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dispatch_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_sent", sa.Boolean(), default=False),
        sa.Column("is_read", sa.Boolean(), default=False),
        sa.Column("send_error", sa.Text(), nullable=True),
        sa.Column("fcm_message_id", sa.String(255), nullable=True),
        sa.Column("twilio_sid", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("dispatch_assignments")
    op.drop_table("reports")
    op.drop_table("hotspots")
    op.drop_table("users")
    # Drop enums
    for enum in ["user_role_enum", "waste_type_enum", "report_status_enum",
                 "hotspot_severity_enum", "vehicle_type_enum", "dispatch_status_enum",
                 "notification_type_enum", "notification_channel_enum"]:
        op.execute(f"DROP TYPE IF EXISTS {enum}")
