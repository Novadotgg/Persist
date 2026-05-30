import httpx
import structlog
from typing import Dict, Any, List, Optional
from app.integrations.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()
youtube_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeConnector:
    """
    HTTP connector for the YouTube Data API v3.
    Uses an API key for public data or OAuth2 access token for user-specific data.
    Uses a Circuit Breaker to isolate connection failures.
    """

    @staticmethod
    @youtube_circuit_breaker
    async def search_videos(
        api_key: str,
        query: str,
        max_results: int = 10,
        order: str = "relevance",
        video_type: str = "video",
    ) -> List[Dict[str, Any]]:
        """
        Searches for YouTube videos matching a query string.
        order: "relevance", "date", "viewCount", "rating"
        """
        logger.info("Searching YouTube videos", query=query)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{YOUTUBE_API_BASE}/search",
                params={
                    "part": "snippet",
                    "q": query,
                    "type": video_type,
                    "maxResults": max_results,
                    "order": order,
                    "key": api_key,
                },
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to search YouTube videos",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json().get("items", [])

    @staticmethod
    @youtube_circuit_breaker
    async def get_video_details(
        api_key: str, video_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Retrieves detailed information for one or more video IDs.
        Returns snippet, contentDetails (duration), statistics (views, likes).
        """
        logger.info("Fetching YouTube video details", video_ids=video_ids)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{YOUTUBE_API_BASE}/videos",
                params={
                    "part": "snippet,contentDetails,statistics",
                    "id": ",".join(video_ids),
                    "key": api_key,
                },
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch YouTube video details",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json().get("items", [])

    @staticmethod
    @youtube_circuit_breaker
    async def get_channel_info(
        api_key: str,
        channel_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves channel metadata by channel ID or username.
        Returns snippet and statistics (subscriber count, total views, video count).
        """
        logger.info("Fetching YouTube channel info")
        params: Dict[str, Any] = {
            "part": "snippet,statistics",
            "key": api_key,
        }
        if channel_id:
            params["id"] = channel_id
        elif username:
            params["forUsername"] = username
        else:
            raise ValueError("Either channel_id or username must be provided.")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{YOUTUBE_API_BASE}/channels", params=params
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch YouTube channel info",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            items = response.json().get("items", [])
            return items[0] if items else {}

    @staticmethod
    @youtube_circuit_breaker
    async def get_playlist_items(
        api_key: str,
        playlist_id: str,
        max_results: int = 25,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves items (videos) in a YouTube playlist.
        """
        logger.info("Fetching YouTube playlist items", playlist_id=playlist_id)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{YOUTUBE_API_BASE}/playlistItems",
                params={
                    "part": "snippet,contentDetails",
                    "playlistId": playlist_id,
                    "maxResults": max_results,
                    "key": api_key,
                },
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch YouTube playlist items",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json().get("items", [])

    @staticmethod
    @youtube_circuit_breaker
    async def get_video_captions_list(
        api_key: str, video_id: str
    ) -> List[Dict[str, Any]]:
        """
        Lists available caption tracks for a YouTube video.
        Note: Downloading captions requires OAuth2 (not API key).
        """
        logger.info("Fetching YouTube captions list", video_id=video_id)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{YOUTUBE_API_BASE}/captions",
                params={"part": "snippet", "videoId": video_id, "key": api_key},
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch YouTube captions",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json().get("items", [])
