import httpx
import structlog
from typing import Dict, Any, Optional
from app.integrations.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()
telegram_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

class TelegramConnector:
    """
    HTTP connector for the Telegram Bot API.
    Provides push notification services to user devices.
    """

    @staticmethod
    @telegram_circuit_breaker
    async def send_alert(bot_token: str, chat_id: str, text: str) -> Dict[str, Any]:
        """
        Sends a rich Markdown push alert via a Telegram Bot.
        """
        if not bot_token or not chat_id:
            logger.error("Telegram bot credentials missing")
            raise ValueError("Telegram Bot token and Chat ID must be provided.")

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }

        logger.info("Sending notification push to Telegram", chat_id=chat_id)
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                logger.error("Failed to send Telegram message", status_code=response.status_code, body=response.text)
                response.raise_for_status()
            
            return response.json()
