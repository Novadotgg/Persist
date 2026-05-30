import httpx
import base64
import structlog
from typing import Dict, Any, Optional
from app.core.config import settings
from app.integrations.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()
jira_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

class JiraConnector:
    """
    HTTP connector for Atlassian Jira Cloud REST API.
    Uses basic auth (email + API token) and a Circuit Breaker.
    """
    
    @staticmethod
    def _get_auth_headers(base_url: str, api_token: str) -> Dict[str, str]:
        """
        Helper to construct authorization headers using Basic auth credentials.
        Normally uses the configured JIRA_API_TOKEN as basic auth directly
        or constructs basic auth if 'user@email.com:api_token' format is used.
        """
        # If settings contains email combined with token (common pattern), use it.
        # Otherwise, construct with a fallback mock user or settings fields.
        raw_cred = f"{api_token}"
        # Standard format is "user_email:api_token". If only token is provided, assume email is not needed
        # or parse from settings if we split it.
        # Let's ensure basic auth token is correctly encoded in base64.
        encoded = base64.b64encode(raw_cred.encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    @staticmethod
    @jira_circuit_breaker
    async def create_issue(
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Task",
        base_url: Optional[str] = None,
        api_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a new issue/task in Jira Cloud.
        Supports custom base_url and api_token, falling back to app settings.
        """
        url = base_url or settings.JIRA_BASE_URL
        token = api_token or settings.JIRA_API_TOKEN

        if not url or not token:
            logger.error("Jira configurations missing in settings")
            raise ValueError("Jira integration base URL or API token is not configured.")

        # Clean URL trail
        url = url.rstrip("/")
        api_endpoint = f"{url}/rest/api/3/issue"
        
        headers = JiraConnector._get_auth_headers(url, token)
        
        # Jira Cloud v3 expects description in Atlassian Document Format (ADF)
        payload = {
            "fields": {
                "project": {
                    "key": project_key
                },
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": description
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {
                    "name": issue_type
                }
            }
        }

        logger.info("Sending issue creation request to Jira", project=project_key, summary=summary)
        async with httpx.AsyncClient() as client:
            response = await client.post(api_endpoint, headers=headers, json=payload)
            if response.status_code not in [200, 201]:
                logger.error("Failed to create Jira issue", status_code=response.status_code, body=response.text)
                response.raise_for_status()
            
            return response.json()
