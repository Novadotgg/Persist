import httpx
import structlog
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.integrations.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()
gmail_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

class GmailConnector:
    """
    HTTP connector for the Google Gmail API using REST endpoints.
    Uses a Circuit Breaker to isolate connection failures.
    """
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

    @staticmethod
    @gmail_circuit_breaker
    async def exchange_auth_code(code: str, code_verifier: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchanges an OAuth2 authorization code for access and refresh tokens.
        Supports PKCE code verifier parameter.
        """
        logger.info("Exchanging Google auth code for tokens")
        data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(GmailConnector.TOKEN_URL, data=data)
            if response.status_code != 200:
                logger.error("Failed Google auth code exchange", status_code=response.status_code, body=response.text)
                response.raise_for_status()
            return response.json()

    @staticmethod
    @gmail_circuit_breaker
    async def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
        """
        Obtains a fresh access token using a refresh token.
        """
        logger.info("Refreshing Google OAuth2 access token")
        data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(GmailConnector.TOKEN_URL, data=data)
            if response.status_code != 200:
                logger.error("Failed Google token refresh", status_code=response.status_code, body=response.text)
                response.raise_for_status()
            return response.json()

    @staticmethod
    @gmail_circuit_breaker
    async def fetch_unread_messages(access_token: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Fetches a list of unread message summaries from Gmail inbox.
        """
        logger.info("Fetching unread Gmail messages list")
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            "q": "is:unread label:INBOX",
            "maxResults": max_results
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GmailConnector.GMAIL_API_BASE}/messages",
                headers=headers,
                params=params
            )
            if response.status_code != 200:
                logger.error("Failed to fetch Gmail message list", status_code=response.status_code, body=response.text)
                response.raise_for_status()
            
            return response.json().get("messages", [])

    @staticmethod
    @gmail_circuit_breaker
    async def get_message_detail(access_token: str, message_id: str) -> Dict[str, Any]:
        """
        Retrieves full details of a specific Gmail message.
        """
        logger.info("Fetching Gmail message details", message_id=message_id)
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GmailConnector.GMAIL_API_BASE}/messages/{message_id}",
                headers=headers
            )
            if response.status_code != 200:
                logger.error("Failed to fetch Gmail message details", message_id=message_id, status_code=response.status_code)
                response.raise_for_status()
            
            return response.json()

    @staticmethod
    def parse_message_payload(msg_detail: Dict[str, Any]) -> Dict[str, Any]:
        """
        Helper utility to extract subject, sender, body snippet, and timestamp
        from Gmail API message detail response payload.
        """
        headers = msg_detail.get("payload", {}).get("headers", [])
        
        subject = "No Subject"
        sender = "Unknown Sender"
        for h in headers:
            name = h.get("name", "").lower()
            if name == "subject":
                subject = h.get("value", subject)
            elif name == "from":
                sender = h.get("value", sender)
        
        body_snippet = msg_detail.get("snippet", "")
        msg_id = msg_detail.get("id")
        
        return {
            "id": msg_id,
            "sender": sender,
            "subject": subject,
            "body": body_snippet
        }
