import httpx
import structlog
from typing import Dict, Any, List, Optional
from app.integrations.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()
slack_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

SLACK_API_BASE = "https://slack.com/api"


class SlackConnector:
    """
    HTTP connector for the Slack Web API.
    Uses a Bot Token (xoxb-...) for authentication.
    All Slack API responses include an "ok" field — check it for errors.
    Uses a Circuit Breaker to isolate connection failures.
    """

    @staticmethod
    def _headers(bot_token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    @staticmethod
    def _check_slack_response(data: Dict[str, Any], method: str) -> None:
        """Raises RuntimeError if Slack API returned ok=false."""
        if not data.get("ok"):
            error = data.get("error", "unknown_error")
            logger.error("Slack API returned error", method=method, error=error)
            raise RuntimeError(f"Slack API error ({method}): {error}")

    @staticmethod
    @slack_circuit_breaker
    async def auth_test(bot_token: str) -> Dict[str, Any]:
        """Verifies the bot token and returns the bot's workspace identity."""
        logger.info("Testing Slack auth")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SLACK_API_BASE}/auth.test",
                headers=SlackConnector._headers(bot_token),
            )
            response.raise_for_status()
            data = response.json()
            SlackConnector._check_slack_response(data, "auth.test")
            return data

    @staticmethod
    @slack_circuit_breaker
    async def list_channels(
        bot_token: str,
        types: str = "public_channel,private_channel",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Lists all accessible channels in the workspace.
        types: comma-separated list of channel types to include.
        """
        logger.info("Listing Slack channels")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SLACK_API_BASE}/conversations.list",
                headers=SlackConnector._headers(bot_token),
                json={"types": types, "limit": limit, "exclude_archived": True},
            )
            response.raise_for_status()
            data = response.json()
            SlackConnector._check_slack_response(data, "conversations.list")
            return data.get("channels", [])

    @staticmethod
    @slack_circuit_breaker
    async def post_message(
        bot_token: str,
        channel: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
        thread_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Posts a message to a Slack channel or DM.
        channel: channel ID (e.g. "C123ABC") or name ("#general") or user ID for DMs.
        blocks: optional Block Kit layout for rich messages.
        thread_ts: optional timestamp to reply in a thread.
        """
        logger.info("Posting Slack message", channel=channel)
        payload: Dict[str, Any] = {"channel": channel, "text": text}
        if blocks:
            payload["blocks"] = blocks
        if thread_ts:
            payload["thread_ts"] = thread_ts

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SLACK_API_BASE}/chat.postMessage",
                headers=SlackConnector._headers(bot_token),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            SlackConnector._check_slack_response(data, "chat.postMessage")
            return data

    @staticmethod
    @slack_circuit_breaker
    async def get_channel_messages(
        bot_token: str,
        channel_id: str,
        limit: int = 50,
        oldest: Optional[str] = None,
        latest: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetches message history from a Slack channel.
        oldest/latest: Unix timestamps for time-bounded queries.
        """
        logger.info("Fetching Slack channel messages", channel_id=channel_id)
        payload: Dict[str, Any] = {"channel": channel_id, "limit": limit}
        if oldest:
            payload["oldest"] = oldest
        if latest:
            payload["latest"] = latest

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SLACK_API_BASE}/conversations.history",
                headers=SlackConnector._headers(bot_token),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            SlackConnector._check_slack_response(data, "conversations.history")
            return data.get("messages", [])

    @staticmethod
    @slack_circuit_breaker
    async def add_reaction(
        bot_token: str,
        channel: str,
        timestamp: str,
        emoji_name: str,
    ) -> bool:
        """
        Adds an emoji reaction to a Slack message.
        emoji_name: name without colons (e.g. "thumbsup", "white_check_mark").
        timestamp: the ts field from the message object.
        """
        logger.info("Adding Slack reaction", emoji=emoji_name, channel=channel)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SLACK_API_BASE}/reactions.add",
                headers=SlackConnector._headers(bot_token),
                json={"channel": channel, "timestamp": timestamp, "name": emoji_name},
            )
            response.raise_for_status()
            data = response.json()
            SlackConnector._check_slack_response(data, "reactions.add")
            return True

    @staticmethod
    @slack_circuit_breaker
    async def lookup_user_by_email(
        bot_token: str, email: str
    ) -> Dict[str, Any]:
        """Looks up a Slack user by their email address."""
        logger.info("Looking up Slack user by email", email=email)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SLACK_API_BASE}/users.lookupByEmail",
                headers=SlackConnector._headers(bot_token),
                params={"email": email},
            )
            response.raise_for_status()
            data = response.json()
            SlackConnector._check_slack_response(data, "users.lookupByEmail")
            return data.get("user", {})

    @staticmethod
    def make_section_block(text: str) -> Dict[str, Any]:
        """Helper to create a Block Kit section block with markdown text."""
        return {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text},
        }

    @staticmethod
    def make_header_block(text: str) -> Dict[str, Any]:
        """Helper to create a Block Kit header block."""
        return {
            "type": "header",
            "text": {"type": "plain_text", "text": text, "emoji": True},
        }
