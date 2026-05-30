import httpx
import structlog
from typing import Dict, Any, List, Optional
from app.integrations.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()
maps_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

MAPS_API_BASE = "https://maps.googleapis.com/maps/api"


class GoogleMapsConnector:
    """
    HTTP connector for the Google Maps Platform REST APIs.
    Covers Geocoding, Directions, and Places APIs.
    Uses an API key for authentication (no OAuth required).
    Uses a Circuit Breaker to isolate connection failures.
    """

    @staticmethod
    @maps_circuit_breaker
    async def geocode(api_key: str, address: str) -> Dict[str, Any]:
        """
        Converts a human-readable address into geographic coordinates (lat/lng).
        Returns the full geocoding result including formatted address and coordinates.
        """
        logger.info("Geocoding address", address=address)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MAPS_API_BASE}/geocode/json",
                params={"address": address, "key": api_key},
            )
            if response.status_code != 200:
                logger.error(
                    "Geocoding request failed",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            data = response.json()
            if data.get("status") not in ["OK", "ZERO_RESULTS"]:
                logger.error("Geocoding API returned error", status=data.get("status"))
            return data

    @staticmethod
    @maps_circuit_breaker
    async def reverse_geocode(
        api_key: str, lat: float, lng: float
    ) -> Dict[str, Any]:
        """
        Converts geographic coordinates into a human-readable address.
        """
        logger.info("Reverse geocoding coordinates", lat=lat, lng=lng)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MAPS_API_BASE}/geocode/json",
                params={"latlng": f"{lat},{lng}", "key": api_key},
            )
            if response.status_code != 200:
                logger.error(
                    "Reverse geocoding request failed",
                    status_code=response.status_code,
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @maps_circuit_breaker
    async def get_directions(
        api_key: str,
        origin: str,
        destination: str,
        mode: str = "driving",
        waypoints: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Returns directions between an origin and destination.
        mode: "driving", "walking", "bicycling", "transit"
        waypoints: optional list of intermediate locations
        """
        logger.info(
            "Fetching Google Maps directions",
            origin=origin,
            destination=destination,
            mode=mode,
        )
        params: Dict[str, Any] = {
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "key": api_key,
        }
        if waypoints:
            params["waypoints"] = "|".join(waypoints)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MAPS_API_BASE}/directions/json", params=params
            )
            if response.status_code != 200:
                logger.error(
                    "Directions request failed",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @maps_circuit_breaker
    async def search_places(
        api_key: str,
        query: str,
        location: Optional[str] = None,
        radius_meters: int = 5000,
    ) -> List[Dict[str, Any]]:
        """
        Searches for places using the Places Text Search API.
        location: "lat,lng" string to bias results geographically.
        """
        logger.info("Searching Google Maps places", query=query)
        params: Dict[str, Any] = {"query": query, "key": api_key}
        if location:
            params["location"] = location
            params["radius"] = radius_meters

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MAPS_API_BASE}/place/textsearch/json", params=params
            )
            if response.status_code != 200:
                logger.error(
                    "Places search failed",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json().get("results", [])

    @staticmethod
    @maps_circuit_breaker
    async def get_place_details(
        api_key: str,
        place_id: str,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves detailed information about a specific place by its place_id.
        fields: comma-separated field mask e.g. "name,rating,formatted_phone_number,opening_hours"
        """
        logger.info("Fetching Google Maps place details", place_id=place_id)
        params: Dict[str, Any] = {"place_id": place_id, "key": api_key}
        if fields:
            params["fields"] = fields

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MAPS_API_BASE}/place/details/json", params=params
            )
            if response.status_code != 200:
                logger.error(
                    "Place details request failed",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json().get("result", {})

    @staticmethod
    @maps_circuit_breaker
    async def get_distance_matrix(
        api_key: str,
        origins: List[str],
        destinations: List[str],
        mode: str = "driving",
    ) -> Dict[str, Any]:
        """
        Calculates travel distances and times between multiple origins and destinations.
        """
        logger.info("Fetching Google Maps distance matrix")
        params = {
            "origins": "|".join(origins),
            "destinations": "|".join(destinations),
            "mode": mode,
            "key": api_key,
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MAPS_API_BASE}/distancematrix/json", params=params
            )
            if response.status_code != 200:
                logger.error(
                    "Distance matrix request failed",
                    status_code=response.status_code,
                )
                response.raise_for_status()
            return response.json()
