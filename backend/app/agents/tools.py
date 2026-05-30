import uuid
import structlog
import httpx
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.integrations.jira import JiraConnector
from app.integrations.telegram import TelegramConnector
from app.integrations.gmail import GmailConnector
from app.integrations.gcal import GoogleCalendarConnector
from app.services.memory_service import search_memories
from app.core.security import decrypt_token
from app.models.models import Integration
from app.core.config import settings

logger = structlog.get_logger()

class BaseTool(ABC):
    """
    Abstract base class for all agent tools.
    """
    name: str
    description: str
    requires_approval: bool = False

    @abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> Any:
        pass


class FetchEmailsTool(BaseTool):
    name = "fetch_emails"
    description = (
        "Fetches the user's unread Gmail messages and returns a summary of each. "
        "No arguments required. Uses stored Google OAuth credentials automatically."
    )
    requires_approval = False

    async def run(self, db: Optional[AsyncSession] = None, max_results: int = 10, **kwargs: Any) -> List[Dict[str, Any]]:
        logger.info("Executing FetchEmailsTool")
        if not db:
            return [{"error": "Database session not provided."}]

        # Get active Google integration
        result = await db.execute(
            select(Integration).where(Integration.provider == "google", Integration.is_active == True)
        )
        integration = result.scalar_one_or_none()
        if not integration:
            return [{"error": "No active Google integration found. Please connect your Google account first."}]

        try:
            refresh_token = decrypt_token(integration.credentials.get("refresh_token", ""))
            token_data = await GmailConnector.refresh_access_token(refresh_token)
            access_token = token_data.get("access_token")
            messages = await GmailConnector.fetch_unread_messages(access_token, max_results=max_results)

            results = []
            for msg in messages[:5]:  # Limit to 5 for context size
                detail = await GmailConnector.get_message_detail(access_token, msg["id"])
                parsed = GmailConnector.parse_message_payload(detail)
                results.append(parsed)
            return results
        except Exception as e:
            logger.error("FetchEmailsTool failed", error=str(e))
            return [{"error": f"Failed to fetch emails: {str(e)}"}]


class FetchCalendarEventsTool(BaseTool):
    name = "fetch_calendar_events"
    description = (
        "Fetches the user's upcoming Google Calendar events. "
        "No arguments required. Uses stored Google OAuth credentials automatically."
    )
    requires_approval = False

    async def run(self, db: Optional[AsyncSession] = None, max_results: int = 5, **kwargs: Any) -> List[Dict[str, Any]]:
        logger.info("Executing FetchCalendarEventsTool")
        if not db:
            return [{"error": "Database session not provided."}]

        result = await db.execute(
            select(Integration).where(Integration.provider == "google", Integration.is_active == True)
        )
        integration = result.scalar_one_or_none()
        if not integration:
            return [{"error": "No active Google integration found. Please connect your Google account first."}]

        try:
            refresh_token = decrypt_token(integration.credentials.get("refresh_token", ""))
            token_data = await GmailConnector.refresh_access_token(refresh_token)
            access_token = token_data.get("access_token")
            events = await GoogleCalendarConnector.fetch_upcoming_events(access_token, max_results=max_results)
            return [
                {
                    "summary": e.get("summary", "No Title"),
                    "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
                    "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
                    "location": e.get("location", ""),
                    "description": e.get("description", "")
                }
                for e in events
            ]
        except Exception as e:
            logger.error("FetchCalendarEventsTool failed", error=str(e))
            return [{"error": f"Failed to fetch calendar events: {str(e)}"}]


class JiraCreateIssueTool(BaseTool):
    name = "jira_create_issue"
    description = (
        "Creates a task/issue ticket in Jira. "
        "Arguments: project_key (str), summary (str), description (str). "
        "Requires human-in-the-loop approval before executing."
    )
    requires_approval = True

    async def run(
        self,
        project_key: str,
        summary: str,
        description: str,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        user_id: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        resolved_url = base_url
        resolved_token = api_token
        
        # Load and decrypt Jira integration credentials from DB if available
        if db and user_id and (not resolved_url or not resolved_token):
            try:
                user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
                query = select(Integration).where(
                    Integration.user_id == user_uuid,
                    Integration.provider == "jira",
                    Integration.is_active == True
                )
                res = await db.execute(query)
                integration = res.scalar_one_or_none()
                if integration and integration.credentials:
                    dec_url = integration.credentials.get("base_url", "")
                    dec_token = decrypt_token(integration.credentials.get("api_token", ""))
                    if dec_url and not resolved_url:
                        resolved_url = dec_url
                    if dec_token and not resolved_token:
                        resolved_token = dec_token
            except Exception as e:
                logger.error("Failed to load Jira credentials from database", error=str(e))
                
        # Fall back to env settings if not configured
        resolved_url = resolved_url or settings.JIRA_BASE_URL
        resolved_token = resolved_token or settings.JIRA_API_TOKEN

        logger.info("Executing JiraCreateIssueTool", project_key=project_key)
        return await JiraConnector.create_issue(
            project_key=project_key,
            summary=summary,
            description=description,
            base_url=resolved_url,
            api_token=resolved_token
        )


class TelegramSendAlertTool(BaseTool):
    name = "telegram_send_alert"
    description = (
        "Sends a push notification to the user's Telegram. "
        "Arguments: text (str) — the message to send. bot_token and chat_id are optional (auto-filled from config)."
    )
    requires_approval = False

    async def run(
        self,
        text: str,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        user_id: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        resolved_token = bot_token
        resolved_chat = chat_id
        
        # Load and decrypt Telegram credentials from DB if available
        if db and user_id and (not resolved_token or not resolved_chat):
            try:
                user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
                query = select(Integration).where(
                    Integration.user_id == user_uuid,
                    Integration.provider == "telegram",
                    Integration.is_active == True
                )
                res = await db.execute(query)
                integration = res.scalar_one_or_none()
                if integration and integration.credentials:
                    dec_token = decrypt_token(integration.credentials.get("bot_token", ""))
                    dec_chat = decrypt_token(integration.credentials.get("chat_id", ""))
                    if dec_token and not resolved_token:
                        resolved_token = dec_token
                    if dec_chat and not resolved_chat:
                        resolved_chat = dec_chat
            except Exception as e:
                logger.error("Failed to load Telegram credentials from database", error=str(e))

        # Fall back to env settings if not configured
        resolved_token = resolved_token or settings.TELEGRAM_BOT_TOKEN
        resolved_chat  = resolved_chat  or settings.TELEGRAM_CHAT_ID

        logger.info("Executing TelegramSendAlertTool", chat_id=resolved_chat)
        return await TelegramConnector.send_alert(
            bot_token=resolved_token,
            chat_id=resolved_chat,
            text=text
        )


class MemorySearchTool(BaseTool):
    name = "memory_search"
    description = (
        "Searches the user's semantic long-term memory for relevant preferences, project history, or older context. "
        "Arguments: query_text (str)."
    )
    requires_approval = False

    async def run(
        self,
        query_text: str,
        db: Optional[AsyncSession] = None,
        limit: int = 5,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        logger.info("Executing MemorySearchTool", query=query_text)
        if not db:
            logger.error("Database session missing in MemorySearchTool execution")
            return [{"error": "Database session not provided."}]
        
        memories = await search_memories(db=db, query_text=query_text, limit=limit)
        return [
            {
                "id": str(m.id),
                "content": m.content,
                "tags": m.tags,
                "importance": m.importance
            } for m in memories
        ]


class FetchTelegramBotMessagesTool(BaseTool):
    name = "fetch_telegram_bot_messages"
    description = (
        "Fetches recent messages sent by the user TO the Telegram bot (via getUpdates). "
        "NOTE: This can only see messages sent directly to the bot, NOT personal Telegram chats. "
        "Arguments: bot_token (str)."
    )
    requires_approval = False

    async def run(self, bot_token: str, limit: int = 10, **kwargs: Any) -> List[Dict[str, Any]]:
        logger.info("Executing FetchTelegramBotMessagesTool")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://api.telegram.org/bot{bot_token}/getUpdates",
                    params={"limit": limit, "allowed_updates": ["message"]}
                )
                data = resp.json()
                if not data.get("ok"):
                    return [{"error": f"Telegram API error: {data.get('description', 'Unknown')}"}]

                updates = data.get("result", [])
                if not updates:
                    return [{"info": "No messages have been sent to the bot recently."}]

                return [
                    {
                        "from": u.get("message", {}).get("from", {}).get("first_name", "Unknown"),
                        "text": u.get("message", {}).get("text", "(no text)"),
                        "date": u.get("message", {}).get("date")
                    }
                    for u in updates
                    if u.get("message")
                ]
        except Exception as e:
            logger.error("FetchTelegramBotMessagesTool failed", error=str(e))
            return [{"error": f"Failed to fetch Telegram updates: {str(e)}"}]


# Registry containing all tools
# DB-dependent tools (need session injection in executor)
DB_TOOLS = {"memory_search", "fetch_emails", "fetch_calendar_events"}

tools_registry: Dict[str, BaseTool] = {
    FetchEmailsTool.name: FetchEmailsTool(),
    FetchCalendarEventsTool.name: FetchCalendarEventsTool(),
    FetchTelegramBotMessagesTool.name: FetchTelegramBotMessagesTool(),
    JiraCreateIssueTool.name: JiraCreateIssueTool(),
    TelegramSendAlertTool.name: TelegramSendAlertTool(),
    MemorySearchTool.name: MemorySearchTool()
}
