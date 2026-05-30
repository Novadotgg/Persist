import httpx
import structlog
from typing import Dict, Any, List, Optional
from app.integrations.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()
discord_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

DISCORD_API_BASE = "https://discord.com/api/v10"


class DiscordConnector:
    """
    HTTP connector for the Discord Bot HTTP API (v10).
    Uses a Discord Bot token for authentication.
    Uses a Circuit Breaker to isolate connection failures.
    """

    @staticmethod
    def _headers(bot_token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    @discord_circuit_breaker
    async def get_bot_info(bot_token: str) -> Dict[str, Any]:
        """Returns information about the authenticated bot user."""
        logger.info("Fetching Discord bot info")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DISCORD_API_BASE}/users/@me",
                headers=DiscordConnector._headers(bot_token),
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch Discord bot info",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @discord_circuit_breaker
    async def get_guild_channels(
        bot_token: str, guild_id: str
    ) -> List[Dict[str, Any]]:
        """
        Returns all channels in a Discord server (guild).
        """
        logger.info("Fetching Discord guild channels", guild_id=guild_id)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DISCORD_API_BASE}/guilds/{guild_id}/channels",
                headers=DiscordConnector._headers(bot_token),
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch Discord channels",
                    guild_id=guild_id,
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @discord_circuit_breaker
    async def send_message(
        bot_token: str,
        channel_id: str,
        content: str,
        embed: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Sends a message to a specific Discord channel.
        Optionally includes a rich embed object.
        """
        logger.info("Sending Discord message", channel_id=channel_id)
        payload: Dict[str, Any] = {"content": content}
        if embed:
            payload["embeds"] = [embed]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{DISCORD_API_BASE}/channels/{channel_id}/messages",
                headers=DiscordConnector._headers(bot_token),
                json=payload,
            )
            if response.status_code not in [200, 201]:
                logger.error(
                    "Failed to send Discord message",
                    channel_id=channel_id,
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @discord_circuit_breaker
    async def get_messages(
        bot_token: str,
        channel_id: str,
        limit: int = 50,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves messages from a Discord channel.
        before/after: message IDs for pagination.
        """
        logger.info("Fetching Discord messages", channel_id=channel_id, limit=limit)
        params: Dict[str, Any] = {"limit": min(limit, 100)}
        if before:
            params["before"] = before
        if after:
            params["after"] = after

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DISCORD_API_BASE}/channels/{channel_id}/messages",
                headers=DiscordConnector._headers(bot_token),
                params=params,
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch Discord messages",
                    channel_id=channel_id,
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @discord_circuit_breaker
    async def add_reaction(
        bot_token: str,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> bool:
        """
        Adds a reaction emoji to a Discord message.
        emoji: unicode emoji (e.g. "✅") or custom emoji format "name:id"
        """
        logger.info(
            "Adding Discord reaction", channel_id=channel_id, message_id=message_id
        )
        # URL-encode the emoji
        import urllib.parse
        encoded_emoji = urllib.parse.quote(emoji)

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{DISCORD_API_BASE}/channels/{channel_id}/messages/{message_id}/reactions/{encoded_emoji}/@me",
                headers=DiscordConnector._headers(bot_token),
            )
            if response.status_code not in [200, 204]:
                logger.error(
                    "Failed to add Discord reaction",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return True

    @staticmethod
    @discord_circuit_breaker
    async def delete_message(
        bot_token: str, channel_id: str, message_id: str
    ) -> bool:
        """Deletes a specific message from a Discord channel."""
        logger.info("Deleting Discord message", message_id=message_id)
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{DISCORD_API_BASE}/channels/{channel_id}/messages/{message_id}",
                headers=DiscordConnector._headers(bot_token),
            )
            if response.status_code not in [200, 204]:
                logger.error(
                    "Failed to delete Discord message",
                    status_code=response.status_code,
                )
                response.raise_for_status()
            return True

    @staticmethod
    def make_embed(
        title: str,
        description: Optional[str] = None,
        color: int = 0x5865F2,
        fields: Optional[List[Dict[str, Any]]] = None,
        footer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Helper to construct a Discord embed object."""
        embed: Dict[str, Any] = {"title": title, "color": color}
        if description:
            embed["description"] = description
        if fields:
            embed["fields"] = fields
        if footer:
            embed["footer"] = {"text": footer}
        return embed
