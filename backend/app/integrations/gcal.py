import httpx
import structlog
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.integrations.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()
gcal_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

class GoogleCalendarConnector:
    """
    HTTP connector for Google Calendar API REST endpoints.
    Uses a Circuit Breaker to isolate connection failures.
    """
    GCAL_API_BASE = "https://www.googleapis.com/calendar/v3/calendars/primary"

    @staticmethod
    @gcal_circuit_breaker
    async def fetch_upcoming_events(access_token: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Fetches upcoming calendar events from the primary calendar starting from current UTC time.
        """
        logger.info("Fetching primary Google Calendar events list")
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Format current time in ISO format (Google Calendar API requires timezone offset or 'Z')
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        params = {
            "timeMin": now_iso,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": max_results
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GoogleCalendarConnector.GCAL_API_BASE}/events",
                headers=headers,
                params=params
            )
            if response.status_code != 200:
                logger.error("Failed to fetch Google Calendar events", status_code=response.status_code, body=response.text)
                response.raise_for_status()
            
            return response.json().get("items", [])

    @staticmethod
    @gcal_circuit_breaker
    async def create_event(access_token: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a new event on the primary calendar.
        """
        logger.info("Creating a new Google Calendar event")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GoogleCalendarConnector.GCAL_API_BASE}/events",
                headers=headers,
                json=event_data
            )
            if response.status_code != 200 and response.status_code != 201:
                logger.error("Failed to create Google Calendar event", status_code=response.status_code, body=response.text)
                response.raise_for_status()
            
            return response.json()
