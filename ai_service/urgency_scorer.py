"""
CleanTrack AI — Urgency Scorer

Urgency = f(waste_type_weight, volume, recurrence, time_of_day, hazard_flag)

Scale: 0 – 100

Urgency weights by waste type:
  hazardous   → base 80 (public health risk)
  organic     → base 60 (smell, vermin attraction)
  mixed       → base 50
  plastic     → base 40 (environmental persistence)
  glass       → base 45 (injury risk)
  metal       → base 35
  cardboard   → base 25
  paper       → base 20
  unknown     → base 30
"""
import math
from datetime import datetime, timezone


# Base urgency weight per waste type (0-100)
WASTE_TYPE_BASE = {
    "hazardous":  80,
    "organic":    60,
    "mixed":      50,
    "glass":      45,
    "plastic":    40,
    "metal":      35,
    "unknown":    30,
    "cardboard":  25,
    "paper":      20,
}


def compute_urgency(
    waste_type: str,
    volume_m3: float,
    recurrence_count: int = 1,
    reported_at: datetime = None,
) -> int:
    """
    Compute an urgency score (0–100) for a waste report.

    Factors:
    - Base type weight
    - Volume bonus: log-scaled, caps at +20
    - Recurrence bonus: sqrt-scaled, caps at +15
    - Time penalty: −5 if reported between 22:00–06:00 (lower response feasibility)
    - Hazard spike: type=hazardous always ≥ 75

    Returns: int score in [0, 100]
    """
    base = WASTE_TYPE_BASE.get(waste_type, 30)

    # Volume bonus (log scale: 0.001 m³ → 0, 1 m³ → ~15, 10 m³ → ~20)
    volume_bonus = min(20, int(math.log1p(volume_m3 * 10) * 6))

    # Recurrence bonus (sqrt: 1 report→0, 5→+6, 10→+9, 20→+13, 50→+15)
    recurrence_bonus = min(15, int(math.sqrt(max(0, recurrence_count - 1)) * 3))

    # Time-of-day factor
    time_penalty = 0
    if reported_at is None:
        reported_at = datetime.now(timezone.utc)
    hour = reported_at.hour
    if hour < 6 or hour >= 22:
        time_penalty = -5  # Late night — lower immediate dispatch feasibility

    raw_score = base + volume_bonus + recurrence_bonus + time_penalty

    # Hazardous floor
    if waste_type == "hazardous":
        raw_score = max(raw_score, 75)

    return max(0, min(100, raw_score))
