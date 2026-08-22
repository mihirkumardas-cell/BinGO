"""
CleanTrack AI — Maps Service
Reverse geocoding, forward geocoding, and routing via Google Maps API.
"""
from typing import Optional

import googlemaps
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class MapsService:
    def __init__(self):
        self._client = None

    def _get_client(self) -> Optional[googlemaps.Client]:
        if not settings.google_maps_api_key:
            return None
        if not self._client:
            self._client = googlemaps.Client(key=settings.google_maps_api_key)
        return self._client

    async def reverse_geocode(
        self, lat: float, lng: float
    ) -> dict:
        """
        Reverse geocode a lat/lng pair.
        Returns dict with: address, city, district, country
        """
        client = self._get_client()
        if not client:
            return {"address": f"{lat:.6f}, {lng:.6f}", "city": None, "district": None}

        try:
            results = client.reverse_geocode((lat, lng))
            if not results:
                return {"address": None, "city": None, "district": None}

            result = results[0]
            formatted_address = result.get("formatted_address", "")
            components = result.get("address_components", [])

            city = next(
                (c["long_name"] for c in components if "locality" in c["types"]), None
            )
            district = next(
                (c["long_name"] for c in components
                 if "administrative_area_level_2" in c["types"]), None
            )

            return {"address": formatted_address, "city": city, "district": district}
        except Exception as e:
            logger.error("reverse_geocode_failed", error=str(e), lat=lat, lng=lng)
            return {"address": None, "city": None, "district": None}

    async def get_route_estimate(
        self, dest_lat: float, dest_lng: float
    ) -> Optional[dict]:
        """
        Get rough ETA and distance to a destination.
        In production this would use the team's current location.
        For now returns a placeholder (real implementation needs origin).
        """
        # In a real system you'd pass the team's GPS coordinates as origin.
        # This method signature is correct — integrate with field agent GPS.
        return None  # Stub: implement with origin coords

    async def geocode(self, address: str) -> Optional[dict]:
        """Forward geocode an address to lat/lng."""
        client = self._get_client()
        if not client:
            return None
        try:
            results = client.geocode(address)
            if results:
                loc = results[0]["geometry"]["location"]
                return {"lat": loc["lat"], "lng": loc["lng"]}
            return None
        except Exception as e:
            logger.error("geocode_failed", error=str(e))
            return None
