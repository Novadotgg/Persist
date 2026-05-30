import httpx
import structlog
from typing import Dict, Any, List, Optional
from app.integrations.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()
gdrive_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

GDRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
GDRIVE_UPLOAD_BASE = "https://www.googleapis.com/upload/drive/v3"


class GoogleDriveConnector:
    """
    HTTP connector for the Google Drive REST API v3.
    Shares the same OAuth2 access token flow as Gmail/GCal (Google provider in DB).
    Uses a Circuit Breaker to isolate connection failures.
    """

    @staticmethod
    @gdrive_circuit_breaker
    async def list_files(
        access_token: str,
        max_results: int = 20,
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Lists files in the user's Google Drive.
        Optionally filters using a Drive query string (e.g. "mimeType='application/pdf'").
        """
        logger.info("Listing Google Drive files", query=query)
        headers = {"Authorization": f"Bearer {access_token}"}
        params: Dict[str, Any] = {
            "pageSize": max_results,
            "fields": "files(id,name,mimeType,size,modifiedTime,webViewLink)",
        }
        if query:
            params["q"] = query

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GDRIVE_API_BASE}/files", headers=headers, params=params
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to list Google Drive files",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json().get("files", [])

    @staticmethod
    @gdrive_circuit_breaker
    async def search_files(
        access_token: str,
        search_term: str,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Full-text searches for files in Drive whose name contains the search term.
        """
        logger.info("Searching Google Drive files", term=search_term)
        query = f"name contains '{search_term}' and trashed = false"
        return await GoogleDriveConnector.list_files(
            access_token=access_token, max_results=max_results, query=query
        )

    @staticmethod
    @gdrive_circuit_breaker
    async def get_file_metadata(
        access_token: str, file_id: str
    ) -> Dict[str, Any]:
        """
        Retrieves metadata for a specific Drive file by its ID.
        """
        logger.info("Fetching Google Drive file metadata", file_id=file_id)
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"fields": "id,name,mimeType,size,modifiedTime,webViewLink,parents"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GDRIVE_API_BASE}/files/{file_id}",
                headers=headers,
                params=params,
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to get Drive file metadata",
                    file_id=file_id,
                    status_code=response.status_code,
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @gdrive_circuit_breaker
    async def create_folder(
        access_token: str,
        folder_name: str,
        parent_folder_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a new folder in Google Drive.
        """
        logger.info("Creating Google Drive folder", name=folder_name)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_folder_id:
            payload["parents"] = [parent_folder_id]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GDRIVE_API_BASE}/files", headers=headers, json=payload
            )
            if response.status_code not in [200, 201]:
                logger.error(
                    "Failed to create Drive folder",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @gdrive_circuit_breaker
    async def download_file_content(
        access_token: str, file_id: str
    ) -> bytes:
        """
        Downloads the raw binary content of a file from Google Drive.
        For Google Docs/Sheets/Slides, use export instead.
        """
        logger.info("Downloading Google Drive file", file_id=file_id)
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{GDRIVE_API_BASE}/files/{file_id}",
                headers=headers,
                params={"alt": "media"},
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to download Drive file",
                    file_id=file_id,
                    status_code=response.status_code,
                )
                response.raise_for_status()
            return response.content
