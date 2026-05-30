import httpx
import structlog
from typing import Dict, Any, List, Optional
from app.integrations.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()
spotify_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

SPOTIFY_API_BASE = "https://api.spotify.com/v1"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"


class SpotifyConnector:
    """
    HTTP connector for the Spotify Web API.
    Supports OAuth2 Authorization Code Flow with PKCE for user-level access.
    Uses a Circuit Breaker to isolate connection failures.
    """

    @staticmethod
    def _headers(access_token: str) -> Dict[str, str]:
        return {"Authorization": f"Bearer {access_token}"}

    @staticmethod
    @spotify_circuit_breaker
    async def refresh_access_token(
        client_id: str, refresh_token: str
    ) -> Dict[str, Any]:
        """
        Refreshes a Spotify access token using the refresh token (PKCE flow).
        """
        logger.info("Refreshing Spotify access token")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                SPOTIFY_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to refresh Spotify token",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @spotify_circuit_breaker
    async def get_currently_playing(access_token: str) -> Optional[Dict[str, Any]]:
        """
        Returns the currently playing track, episode, or None if nothing is playing.
        """
        logger.info("Fetching Spotify currently playing track")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SPOTIFY_API_BASE}/me/player/currently-playing",
                headers=SpotifyConnector._headers(access_token),
            )
            if response.status_code == 204:
                # 204 means nothing is currently playing
                return None
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch Spotify currently playing",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @spotify_circuit_breaker
    async def get_playback_state(access_token: str) -> Optional[Dict[str, Any]]:
        """
        Returns the full playback state (device, shuffle, repeat, progress, track).
        """
        logger.info("Fetching Spotify playback state")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SPOTIFY_API_BASE}/me/player",
                headers=SpotifyConnector._headers(access_token),
            )
            if response.status_code == 204:
                return None
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch Spotify playback state",
                    status_code=response.status_code,
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @spotify_circuit_breaker
    async def search_tracks(
        access_token: str, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Searches for tracks on Spotify matching the given query string.
        """
        logger.info("Searching Spotify tracks", query=query)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SPOTIFY_API_BASE}/search",
                headers=SpotifyConnector._headers(access_token),
                params={"q": query, "type": "track", "limit": limit},
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to search Spotify tracks",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json().get("tracks", {}).get("items", [])

    @staticmethod
    @spotify_circuit_breaker
    async def play(
        access_token: str,
        uris: Optional[List[str]] = None,
        context_uri: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> bool:
        """
        Starts or resumes playback. Optionally plays specific track URIs or a context (album/playlist).
        """
        logger.info("Starting Spotify playback")
        params: Dict[str, Any] = {}
        if device_id:
            params["device_id"] = device_id

        payload: Dict[str, Any] = {}
        if uris:
            payload["uris"] = uris
        elif context_uri:
            payload["context_uri"] = context_uri

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{SPOTIFY_API_BASE}/me/player/play",
                headers=SpotifyConnector._headers(access_token),
                params=params,
                json=payload,
            )
            if response.status_code not in [200, 204]:
                logger.error(
                    "Failed to start Spotify playback",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return True

    @staticmethod
    @spotify_circuit_breaker
    async def pause(access_token: str, device_id: Optional[str] = None) -> bool:
        """Pauses Spotify playback on the active device."""
        logger.info("Pausing Spotify playback")
        params = {"device_id": device_id} if device_id else {}
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{SPOTIFY_API_BASE}/me/player/pause",
                headers=SpotifyConnector._headers(access_token),
                params=params,
            )
            if response.status_code not in [200, 204]:
                logger.error(
                    "Failed to pause Spotify playback",
                    status_code=response.status_code,
                )
                response.raise_for_status()
            return True

    @staticmethod
    @spotify_circuit_breaker
    async def skip_next(access_token: str, device_id: Optional[str] = None) -> bool:
        """Skips to the next track in the playback queue."""
        logger.info("Skipping to next Spotify track")
        params = {"device_id": device_id} if device_id else {}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SPOTIFY_API_BASE}/me/player/next",
                headers=SpotifyConnector._headers(access_token),
                params=params,
            )
            if response.status_code not in [200, 204]:
                logger.error(
                    "Failed to skip Spotify track",
                    status_code=response.status_code,
                )
                response.raise_for_status()
            return True

    @staticmethod
    @spotify_circuit_breaker
    async def get_playlists(
        access_token: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Returns the current user's playlists."""
        logger.info("Fetching Spotify playlists")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SPOTIFY_API_BASE}/me/playlists",
                headers=SpotifyConnector._headers(access_token),
                params={"limit": limit},
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch Spotify playlists",
                    status_code=response.status_code,
                )
                response.raise_for_status()
            return response.json().get("items", [])

    @staticmethod
    @spotify_circuit_breaker
    async def get_available_devices(access_token: str) -> List[Dict[str, Any]]:
        """Returns a list of available Spotify devices for the user."""
        logger.info("Fetching Spotify available devices")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SPOTIFY_API_BASE}/me/player/devices",
                headers=SpotifyConnector._headers(access_token),
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch Spotify devices",
                    status_code=response.status_code,
                )
                response.raise_for_status()
            return response.json().get("devices", [])
