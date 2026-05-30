import httpx
import structlog
from typing import Dict, Any, List, Optional
from app.integrations.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()
github_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

GITHUB_API_BASE = "https://api.github.com"


class GitHubConnector:
    """
    HTTP connector for the GitHub REST API v3.
    Uses a Personal Access Token (PAT) for authentication.
    Uses a Circuit Breaker to isolate connection failures.
    """

    @staticmethod
    def _headers(pat: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {pat}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    @staticmethod
    @github_circuit_breaker
    async def get_authenticated_user(pat: str) -> Dict[str, Any]:
        """Returns the authenticated user's GitHub profile."""
        logger.info("Fetching GitHub authenticated user")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/user",
                headers=GitHubConnector._headers(pat),
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch GitHub user",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @github_circuit_breaker
    async def list_repos(
        pat: str, visibility: str = "all", max_results: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Lists repositories for the authenticated user.
        visibility: "all", "public", "private"
        """
        logger.info("Listing GitHub repos", visibility=visibility)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/user/repos",
                headers=GitHubConnector._headers(pat),
                params={
                    "visibility": visibility,
                    "per_page": max_results,
                    "sort": "updated",
                },
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to list GitHub repos",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @github_circuit_breaker
    async def get_repo(pat: str, owner: str, repo: str) -> Dict[str, Any]:
        """
        Fetches details for a specific GitHub repository.
        """
        logger.info("Fetching GitHub repo", owner=owner, repo=repo)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}",
                headers=GitHubConnector._headers(pat),
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch GitHub repo",
                    owner=owner,
                    repo=repo,
                    status_code=response.status_code,
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @github_circuit_breaker
    async def list_issues(
        pat: str,
        owner: str,
        repo: str,
        state: str = "open",
        max_results: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Lists issues for a repository.
        state: "open", "closed", "all"
        """
        logger.info("Listing GitHub issues", owner=owner, repo=repo, state=state)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues",
                headers=GitHubConnector._headers(pat),
                params={"state": state, "per_page": max_results},
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to list GitHub issues",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @github_circuit_breaker
    async def create_issue(
        pat: str,
        owner: str,
        repo: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Creates a new issue in a GitHub repository.
        """
        logger.info("Creating GitHub issue", owner=owner, repo=repo, title=title)
        payload: Dict[str, Any] = {"title": title}
        if body:
            payload["body"] = body
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues",
                headers=GitHubConnector._headers(pat),
                json=payload,
            )
            if response.status_code not in [200, 201]:
                logger.error(
                    "Failed to create GitHub issue",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @github_circuit_breaker
    async def list_pull_requests(
        pat: str,
        owner: str,
        repo: str,
        state: str = "open",
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Lists pull requests for a repository.
        state: "open", "closed", "all"
        """
        logger.info("Listing GitHub PRs", owner=owner, repo=repo, state=state)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls",
                headers=GitHubConnector._headers(pat),
                params={"state": state, "per_page": max_results},
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to list GitHub PRs",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @github_circuit_breaker
    async def get_notifications(
        pat: str, all_notifications: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Returns the authenticated user's unread GitHub notifications.
        all_notifications: if True, returns all notifications including read ones.
        """
        logger.info("Fetching GitHub notifications")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/notifications",
                headers=GitHubConnector._headers(pat),
                params={"all": str(all_notifications).lower()},
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch GitHub notifications",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @github_circuit_breaker
    async def search_code(
        pat: str, query: str, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Searches code across GitHub repositories.
        query: supports GitHub search syntax e.g. "filename:config.py repo:owner/repo"
        """
        logger.info("Searching GitHub code", query=query)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/search/code",
                headers=GitHubConnector._headers(pat),
                params={"q": query, "per_page": max_results},
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to search GitHub code",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json().get("items", [])
