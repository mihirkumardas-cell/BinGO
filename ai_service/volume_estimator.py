"""
CleanTrack AI — Volume Estimator
Estimates waste volume in cubic metres from bounding box area.

Method:
  Volume = (bbox_area_fraction × avg_depth_coefficient[waste_type]) × scene_scale_factor

  avg_depth_coefficient: empirical depth-per-area ratio for each waste category,
  derived from TACO dataset annotations and physical waste density standards.
  These are conservative estimates suitable for triage (not precise measurement).

  scene_scale_factor: assumes average street-level photo from ~2m distance,
  resulting in a typical scene width of ~4m (standard sidewalk).
"""
from typing import Optional

# Depth coefficients (metres) per waste type — based on waste volume studies
# Source: Environmental Engineering waste density standards + TACO visual analysis
WASTE_DEPTH_COEFFICIENTS = {
    "plastic":    0.15,   # Plastic bags/bottles — shallow but wide
    "cardboard":  0.25,   # Flattened boxes — moderate depth
    "glass":      0.20,   # Glass bottles — compact
    "metal":      0.18,   # Cans — moderate
    "paper":      0.12,   # Flat paper — minimal depth
    "organic":    0.35,   # Food waste — variable, deeper
    "hazardous":  0.10,   # Small hazardous items
    "mixed":      0.28,   # Mixed refuse — average
    "unknown":    0.20,   # Conservative default
}

# Assumed scene width at street level (~4m for standard photo distance)
SCENE_WIDTH_METRES = 4.0


def estimate_volume(
    waste_type: str,
    bounding_box: Optional[dict],
    image_width: int = 1920,
    image_height: int = 1080,
) -> float:
    """
    Estimate waste volume in cubic metres.

    Args:
        waste_type: CleanTrack waste type string
        bounding_box: normalised bbox dict {x, y, width, height}
        image_width: original image width in pixels
        image_height: original image height in pixels

    Returns:
        volume_m3: estimated volume (minimum 0.001 m³)
    """
    if not bounding_box:
        # No bbox detected — use minimal estimate for the waste type
        depth = WASTE_DEPTH_COEFFICIENTS.get(waste_type, 0.20)
        return round(0.1 * 0.1 * depth, 4)  # 10cm x 10cm default

    bbox_width_fraction = bounding_box.get("width", 0.1)
    bbox_height_fraction = bounding_box.get("height", 0.1)

    # Convert normalised bbox to real-world dimensions (metres)
    aspect_ratio = image_width / image_height
    scene_height_metres = SCENE_WIDTH_METRES / aspect_ratio

    real_width_m = bbox_width_fraction * SCENE_WIDTH_METRES
    real_height_m = bbox_height_fraction * scene_height_metres

    # Area in m²
    area_m2 = real_width_m * real_height_m

    # Depth coefficient
    depth_m = WASTE_DEPTH_COEFFICIENTS.get(waste_type, 0.20)

    volume_m3 = area_m2 * depth_m

    # Clamp to reasonable range [0.001, 50] m³
    return round(max(0.001, min(volume_m3, 50.0)), 4)
