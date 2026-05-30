import httpx
import structlog
from typing import Dict, Any, List, Optional
from app.integrations.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()
todoist_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

TODOIST_API_BASE = "https://api.todoist.com/rest/v2"


class TodoistConnector:
    """
    HTTP connector for the Todoist REST API v2.
    Uses a Bearer API token for authentication.
    Uses a Circuit Breaker to isolate connection failures.
    """

    @staticmethod
    def _headers(api_token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    @todoist_circuit_breaker
    async def get_projects(api_token: str) -> List[Dict[str, Any]]:
        """
        Returns all Todoist projects for the authenticated user.
        """
        logger.info("Fetching Todoist projects")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TODOIST_API_BASE}/projects",
                headers=TodoistConnector._headers(api_token),
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch Todoist projects",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @todoist_circuit_breaker
    async def get_tasks(
        api_token: str,
        project_id: Optional[str] = None,
        filter_str: Optional[str] = None,
        label: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Returns active tasks, optionally filtered by project, filter string, or label.
        """
        logger.info("Fetching Todoist tasks", project_id=project_id)
        params: Dict[str, Any] = {}
        if project_id:
            params["project_id"] = project_id
        if filter_str:
            params["filter"] = filter_str
        if label:
            params["label"] = label

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TODOIST_API_BASE}/tasks",
                headers=TodoistConnector._headers(api_token),
                params=params,
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch Todoist tasks",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @todoist_circuit_breaker
    async def create_task(
        api_token: str,
        content: str,
        project_id: Optional[str] = None,
        due_string: Optional[str] = None,
        priority: int = 1,
        description: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Creates a new Todoist task.
        priority: 1 (normal) to 4 (very urgent).
        due_string: natural language due date, e.g. "tomorrow at 5pm".
        """
        logger.info("Creating Todoist task", content=content)
        payload: Dict[str, Any] = {
            "content": content,
            "priority": priority,
        }
        if project_id:
            payload["project_id"] = project_id
        if due_string:
            payload["due_string"] = due_string
        if description:
            payload["description"] = description
        if labels:
            payload["labels"] = labels

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TODOIST_API_BASE}/tasks",
                headers=TodoistConnector._headers(api_token),
                json=payload,
            )
            if response.status_code not in [200, 201, 204]:
                logger.error(
                    "Failed to create Todoist task",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @todoist_circuit_breaker
    async def complete_task(api_token: str, task_id: str) -> bool:
        """
        Marks a Todoist task as completed.
        Returns True on success.
        """
        logger.info("Completing Todoist task", task_id=task_id)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TODOIST_API_BASE}/tasks/{task_id}/close",
                headers=TodoistConnector._headers(api_token),
            )
            if response.status_code not in [200, 204]:
                logger.error(
                    "Failed to complete Todoist task",
                    task_id=task_id,
                    status_code=response.status_code,
                )
                response.raise_for_status()
            return True

    @staticmethod
    @todoist_circuit_breaker
    async def delete_task(api_token: str, task_id: str) -> bool:
        """
        Permanently deletes a Todoist task.
        Returns True on success.
        """
        logger.info("Deleting Todoist task", task_id=task_id)
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{TODOIST_API_BASE}/tasks/{task_id}",
                headers=TodoistConnector._headers(api_token),
            )
            if response.status_code not in [200, 204]:
                logger.error(
                    "Failed to delete Todoist task",
                    task_id=task_id,
                    status_code=response.status_code,
                )
                response.raise_for_status()
            return True
