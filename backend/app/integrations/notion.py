import httpx
import structlog
from typing import Dict, Any, List, Optional
from app.integrations.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()
notion_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionConnector:
    """
    HTTP connector for the Notion API v1.
    Uses an internal integration token (Bearer) for authentication.
    Uses a Circuit Breaker to isolate connection failures.
    """

    @staticmethod
    def _headers(api_token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {api_token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    @staticmethod
    @notion_circuit_breaker
    async def search_pages(
        api_token: str, query: str = "", max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Searches across all pages and databases the integration has access to.
        """
        logger.info("Searching Notion pages", query=query)
        payload: Dict[str, Any] = {"page_size": max_results}
        if query:
            payload["query"] = query

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{NOTION_API_BASE}/search",
                headers=NotionConnector._headers(api_token),
                json=payload,
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to search Notion pages",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json().get("results", [])

    @staticmethod
    @notion_circuit_breaker
    async def get_page(api_token: str, page_id: str) -> Dict[str, Any]:
        """
        Retrieves a Notion page's metadata and properties by its ID.
        """
        logger.info("Fetching Notion page", page_id=page_id)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{NOTION_API_BASE}/pages/{page_id}",
                headers=NotionConnector._headers(api_token),
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch Notion page",
                    page_id=page_id,
                    status_code=response.status_code,
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @notion_circuit_breaker
    async def create_page(
        api_token: str,
        parent_page_id: str,
        title: str,
        content_blocks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Creates a new Notion page under a given parent page.
        content_blocks should be a list of Notion block objects.
        """
        logger.info("Creating Notion page", title=title, parent=parent_page_id)
        payload: Dict[str, Any] = {
            "parent": {"page_id": parent_page_id},
            "properties": {
                "title": {
                    "title": [{"type": "text", "text": {"content": title}}]
                }
            },
        }
        if content_blocks:
            payload["children"] = content_blocks

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{NOTION_API_BASE}/pages",
                headers=NotionConnector._headers(api_token),
                json=payload,
            )
            if response.status_code not in [200, 201]:
                logger.error(
                    "Failed to create Notion page",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @notion_circuit_breaker
    async def append_blocks(
        api_token: str, block_id: str, children: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Appends new content blocks to an existing Notion page or block.
        """
        logger.info("Appending blocks to Notion block", block_id=block_id)
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{NOTION_API_BASE}/blocks/{block_id}/children",
                headers=NotionConnector._headers(api_token),
                json={"children": children},
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to append Notion blocks",
                    block_id=block_id,
                    status_code=response.status_code,
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @notion_circuit_breaker
    async def query_database(
        api_token: str,
        database_id: str,
        filter_payload: Optional[Dict[str, Any]] = None,
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Queries a Notion database and returns its page results.
        """
        logger.info("Querying Notion database", database_id=database_id)
        payload: Dict[str, Any] = {"page_size": max_results}
        if filter_payload:
            payload["filter"] = filter_payload

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{NOTION_API_BASE}/databases/{database_id}/query",
                headers=NotionConnector._headers(api_token),
                json=payload,
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to query Notion database",
                    database_id=database_id,
                    status_code=response.status_code,
                )
                response.raise_for_status()
            return response.json().get("results", [])

    @staticmethod
    def make_text_block(text: str) -> Dict[str, Any]:
        """Helper to create a simple paragraph block for Notion."""
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            },
        }
