"""
CleanTrack AI — Database Seeding
Populates initial demo & production users, hotspots, reports, and dispatch records.
"""
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from geoalchemy2.elements import WKTElement
from sqlalchemy import select, func

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.dispatch import DispatchAssignment, DispatchStatus, VehicleType
from app.models.hotspot import Hotspot, HotspotSeverity
from app.models.report import Report, ReportStatus, WasteType
from app.models.user import User, UserRole

logger = structlog.get_logger()


async def seed_database() -> None:
    """Seed initial data if database has no reports or users."""
    async with AsyncSessionLocal() as db:
        try:
            # Check if database already has users
            user_count = (await db.execute(select(func.count(User.id)))).scalar_one()
            report_count = (await db.execute(select(func.count(Report.id)))).scalar_one()

            if user_count > 0 and report_count > 0:
                logger.info("database_already_seeded", users=user_count, reports=report_count)
                return

            logger.info("seeding_initial_database_data")
            now = datetime.now(timezone.utc)

            # 1. Create Core Users
            admin = User(
                id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                email="admin@bingo.app",
                full_name="BinGO Municipal Admin",
                hashed_password=hash_password("admin123"),
                role=UserRole.SUPER_ADMIN.value,
                is_active=True,
                is_verified=True,
                assigned_zone="Metro Area 1",
            )
            agent = User(
                id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
                email="agent@bingo.app",
                full_name="Fleet Officer Alex Ramos",
                hashed_password=hash_password("agent123"),
                role=UserRole.FIELD_AGENT.value,
                is_active=True,
                is_verified=True,
                assigned_zone="Sector 4 (Central)",
            )
            citizen = User(
                id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
                email="citizen@bingo.app",
                full_name="Jane Doe (Citizen)",
                hashed_password=hash_password("citizen123"),
                role=UserRole.CITIZEN.value,
                is_active=True,
                is_verified=True,
            )

            if user_count == 0:
                db.add_all([admin, agent, citizen])
                await db.flush()

            # 2. Create Hotspots
            hs1 = Hotspot(
                id=uuid.UUID("11111111-1111-1111-1111-111111111101"),
                centroid_lat=40.7580,
                centroid_lng=-73.9855,
                centroid=WKTElement("POINT(-73.9855 40.7580)", srid=4326),
                address="Times Square / 42nd St Commercial Hub",
                district="Manhattan Central",
                report_count=14,
                severity=HotspotSeverity.CRITICAL.value,
                dominant_waste_type="hazardous",
                avg_urgency_score=88.5,
                radius_meters=180.0,
                is_active=True,
                first_reported_at=now - timedelta(days=5),
                last_reported_at=now - timedelta(minutes=15),
            )
            hs2 = Hotspot(
                id=uuid.UUID("11111111-1111-1111-1111-111111111102"),
                centroid_lat=40.7128,
                centroid_lng=-74.0060,
                centroid=WKTElement("POINT(-74.0060 40.7128)", srid=4326),
                address="Civic Center Plaza & Transit Junction",
                district="Lower Manhattan",
                report_count=9,
                severity=HotspotSeverity.HIGH.value,
                dominant_waste_type="plastic",
                avg_urgency_score=68.0,
                radius_meters=140.0,
                is_active=True,
                first_reported_at=now - timedelta(days=3),
                last_reported_at=now - timedelta(hours=1),
            )
            hs3 = Hotspot(
                id=uuid.UUID("11111111-1111-1111-1111-111111111103"),
                centroid_lat=40.7484,
                centroid_lng=-73.9857,
                centroid=WKTElement("POINT(-73.9857 40.7484)", srid=4326),
                address="Garment District Sector 2 Alleyway",
                district="Midtown South",
                report_count=5,
                severity=HotspotSeverity.MEDIUM.value,
                dominant_waste_type="cardboard",
                avg_urgency_score=48.0,
                radius_meters=95.0,
                is_active=True,
                first_reported_at=now - timedelta(days=2),
                last_reported_at=now - timedelta(hours=4),
            )

            db.add_all([hs1, hs2, hs3])
            await db.flush()

            # 3. Create Reports
            reports_data = [
                {
                    "id": uuid.UUID("22222222-2222-2222-2222-222222222201"),
                    "reporter_id": citizen.id,
                    "latitude": 40.7580,
                    "longitude": -73.9855,
                    "address": "742 Broadway St, Times Square",
                    "city": "New York",
                    "district": "Manhattan Central",
                    "waste_type": WasteType.HAZARDOUS,
                    "ai_confidence": 0.95,
                    "volume_estimate_m3": 1.45,
                    "urgency_score": 92,
                    "status": ReportStatus.VERIFIED,
                    "hotspot_id": hs1.id,
                    "recommended_vehicle": "Hazmat Containment Unit",
                    "recommended_team_size": 3,
                    "description": "Chemical solvent containers leaking near sidewalk storm drain.",
                    "created_at": now - timedelta(minutes=35),
                },
                {
                    "id": uuid.UUID("22222222-2222-2222-2222-222222222202"),
                    "reporter_id": citizen.id,
                    "latitude": 40.7585,
                    "longitude": -73.9850,
                    "address": "42nd St & 7th Ave",
                    "city": "New York",
                    "district": "Manhattan Central",
                    "waste_type": WasteType.MIXED,
                    "ai_confidence": 0.92,
                    "volume_estimate_m3": 2.80,
                    "urgency_score": 85,
                    "status": ReportStatus.PENDING_AI,
                    "hotspot_id": hs1.id,
                    "recommended_vehicle": "Heavy Bulk Tipper",
                    "recommended_team_size": 2,
                    "description": "Large overflow of bulk mixed trash blocking pedestrian ramp.",
                    "created_at": now - timedelta(minutes=10),
                },
                {
                    "id": uuid.UUID("22222222-2222-2222-2222-222222222203"),
                    "reporter_id": citizen.id,
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "address": "Civic Center Park Walkway",
                    "city": "New York",
                    "district": "Lower Manhattan",
                    "waste_type": WasteType.PLASTIC,
                    "ai_confidence": 0.89,
                    "volume_estimate_m3": 0.65,
                    "urgency_score": 72,
                    "status": ReportStatus.DISPATCHED,
                    "hotspot_id": hs2.id,
                    "recommended_vehicle": "Compact Tipper Van",
                    "recommended_team_size": 2,
                    "description": "Accumulation of plastic bottles and packaging near park fountain.",
                    "created_at": now - timedelta(hours=1, minutes=20),
                },
                {
                    "id": uuid.UUID("22222222-2222-2222-2222-222222222204"),
                    "reporter_id": citizen.id,
                    "latitude": 40.7484,
                    "longitude": -73.9857,
                    "address": "350 5th Ave Commercial Alley",
                    "city": "New York",
                    "district": "Midtown South",
                    "waste_type": WasteType.CARDBOARD,
                    "ai_confidence": 0.88,
                    "volume_estimate_m3": 1.10,
                    "urgency_score": 45,
                    "status": ReportStatus.VERIFIED,
                    "hotspot_id": hs3.id,
                    "recommended_vehicle": "Standard Collection Truck",
                    "recommended_team_size": 2,
                    "description": "Flattened and wet commercial cardboard boxes stacked on sidewalk.",
                    "created_at": now - timedelta(hours=2, minutes=45),
                },
                {
                    "id": uuid.UUID("22222222-2222-2222-2222-222222222205"),
                    "reporter_id": citizen.id,
                    "latitude": 40.7290,
                    "longitude": -73.9965,
                    "address": "Washington Square Park East",
                    "city": "New York",
                    "district": "Greenwich Village",
                    "waste_type": WasteType.ORGANIC,
                    "ai_confidence": 0.83,
                    "volume_estimate_m3": 0.40,
                    "urgency_score": 61,
                    "status": ReportStatus.RESOLVED,
                    "recommended_vehicle": "Rapid Clean Crew",
                    "recommended_team_size": 1,
                    "description": "Compostable market scraps cleared by morning maintenance team.",
                    "created_at": now - timedelta(hours=5),
                    "resolved_at": now - timedelta(hours=2),
                },
                {
                    "id": uuid.UUID("22222222-2222-2222-2222-222222222206"),
                    "reporter_id": citizen.id,
                    "latitude": 40.7061,
                    "longitude": -74.0092,
                    "address": "Wall Street Corridor",
                    "city": "New York",
                    "district": "Financial District",
                    "waste_type": WasteType.METAL,
                    "ai_confidence": 0.91,
                    "volume_estimate_m3": 0.85,
                    "urgency_score": 58,
                    "status": ReportStatus.AI_PROCESSED,
                    "recommended_vehicle": "Standard Collection Truck",
                    "recommended_team_size": 2,
                    "description": "Discarded metal pipes and construction scrap near curb.",
                    "created_at": now - timedelta(hours=3),
                },
            ]

            created_reports = []
            for r_data in reports_data:
                point_wkt = f"POINT({r_data['longitude']} {r_data['latitude']})"
                rep = Report(
                    id=r_data["id"],
                    reporter_id=r_data["reporter_id"],
                    latitude=r_data["latitude"],
                    longitude=r_data["longitude"],
                    location=WKTElement(point_wkt, srid=4326),
                    address=r_data["address"],
                    city=r_data["city"],
                    district=r_data["district"],
                    waste_type=r_data["waste_type"].value if hasattr(r_data["waste_type"], "value") else r_data["waste_type"],
                    ai_confidence=r_data["ai_confidence"],
                    volume_estimate_m3=r_data["volume_estimate_m3"],
                    urgency_score=r_data["urgency_score"],
                    status=r_data["status"].value if hasattr(r_data["status"], "value") else r_data["status"],
                    hotspot_id=r_data.get("hotspot_id"),
                    recommended_vehicle=r_data.get("recommended_vehicle"),
                    recommended_team_size=r_data.get("recommended_team_size", 2),
                    description=r_data.get("description"),
                    created_at=r_data["created_at"],
                    resolved_at=r_data.get("resolved_at"),
                )
                db.add(rep)
                created_reports.append(rep)

            await db.flush()

            # 4. Create Dispatch Assignments
            disp1 = DispatchAssignment(
                id=uuid.UUID("33333333-3333-3333-3333-333333333301"),
                report_id=created_reports[2].id,  # R-003 Dispatched
                team_id="Unit 7 — Compact Tipper",
                team_name="Sector 4 Rapid Clean Crew",
                field_agent_id=agent.id,
                vehicle_type=VehicleType.COMPACT_VAN.value,
                vehicle_id="Ford F-550 (NYC-882)",
                team_size=2,
                status=DispatchStatus.EN_ROUTE.value,
                estimated_arrival_minutes=8,
                distance_km=2.4,
                notes="Priority plastic pickup at Civic Center Plaza.",
                assigned_at=now - timedelta(minutes=20),
            )
            disp2 = DispatchAssignment(
                id=uuid.UUID("33333333-3333-3333-3333-333333333302"),
                hotspot_id=hs1.id,  # HS-101 Critical
                team_id="Unit 3 — Heavy Hauler",
                team_name="Metro Hazmat & Bulk Division",
                field_agent_id=agent.id,
                vehicle_type=VehicleType.HAZMAT_UNIT.value,
                vehicle_id="Volvo FM Dump Truck (NYC-104)",
                team_size=3,
                status=DispatchStatus.IN_PROGRESS.value,
                estimated_arrival_minutes=0,
                distance_km=0.0,
                notes="Active containment operation on Times Square chemical spill.",
                assigned_at=now - timedelta(minutes=45),
            )

            db.add_all([disp1, disp2])
            await db.commit()
            logger.info("database_seeded_successfully", reports=len(created_reports), hotspots=3)

        except Exception as e:
            await db.rollback()
            logger.error("database_seeding_failed", error=str(e))
