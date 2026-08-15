"""
CleanTrack AI — Dispatch Recommender

Maps (waste_type, volume) → (vehicle_type, team_size)
This is a rule-based expert system seeded by the TACO dataset category analysis
and municipal sanitation operations best practices.

Vehicle fleet definition (matches VehicleType enum in main app):
  motorcycle        — rapid assessment / small items, 1 person
  compact_van       — small volume (<0.5 m³), narrow streets, 2 persons
  collection_truck  — standard collection, 2-4 persons
  bulk_loader       — large volume (>5 m³), construction debris, 4 persons
  hazmat_unit       — hazardous waste only, 2 trained specialists
  street_sweeper    — scattered litter over large area, 1-2 persons
"""
from typing import Tuple


# Rules: (waste_type, volume_m3_min, volume_m3_max) → (vehicle, team_size)
# Evaluated in order — first match wins
DISPATCH_RULES = [
    # Hazardous — always hazmat regardless of volume
    ("hazardous",   0.0,    999,  "hazmat_unit",       2),

    # Organic — smell urgency drives truck even for small volume
    ("organic",     0.0,    0.3,  "compact_van",       2),
    ("organic",     0.3,    999,  "collection_truck",  3),

    # Plastic — lightweight but high visual impact
    ("plastic",     0.0,    0.2,  "compact_van",       2),
    ("plastic",     0.2,    3.0,  "collection_truck",  2),
    ("plastic",     3.0,    999,  "collection_truck",  4),

    # Glass — injury risk, careful handling
    ("glass",       0.0,    0.5,  "compact_van",       2),
    ("glass",       0.5,    999,  "collection_truck",  3),

    # Metal
    ("metal",       0.0,    1.0,  "compact_van",       2),
    ("metal",       1.0,    10,   "collection_truck",  3),
    ("metal",       10,     999,  "bulk_loader",       4),

    # Paper / Cardboard — scattered litter → sweeper
    ("paper",       0.0,    0.1,  "motorcycle",        1),
    ("paper",       0.1,    999,  "collection_truck",  2),
    ("cardboard",   0.0,    0.5,  "compact_van",       2),
    ("cardboard",   0.5,    999,  "collection_truck",  2),

    # Mixed / Unknown — default truck
    ("mixed",       0.0,    2.0,  "collection_truck",  2),
    ("mixed",       2.0,    10,   "collection_truck",  3),
    ("mixed",       10,     999,  "bulk_loader",       4),
    ("unknown",     0.0,    999,  "collection_truck",  2),
]


def recommend_dispatch(
    waste_type: str,
    volume_m3: float,
) -> Tuple[str, int]:
    """
    Returns (vehicle_type_string, team_size).
    Uses first-match rule table.
    """
    for rule_type, vol_min, vol_max, vehicle, team_size in DISPATCH_RULES:
        if rule_type == waste_type and vol_min <= volume_m3 < vol_max:
            return vehicle, team_size

    # Default fallback
    return "collection_truck", 2
