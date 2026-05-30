import httpx
import structlog
from typing import Dict, Any, Optional
from app.integrations.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()
whatsapp_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


class WhatsAppConnector:
    """
    HTTP connector for the WhatsApp Business Cloud API (Meta Graph API v19.0).
    Requires a WhatsApp Business Account, phone number ID, and permanent access token.
    Uses a Circuit Breaker to isolate connection failures.
    """

    @staticmethod
    def _headers(access_token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    @whatsapp_circuit_breaker
    async def send_text_message(
        access_token: str,
        phone_number_id: str,
        to: str,
        text: str,
        preview_url: bool = False,
    ) -> Dict[str, Any]:
        """
        Sends a text message to a WhatsApp number.
        `to` must be the full phone number in E.164 format (e.g. "+15551234567").
        """
        logger.info("Sending WhatsApp text message", to=to)
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": text,
            },
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GRAPH_API_BASE}/{phone_number_id}/messages",
                headers=WhatsAppConnector._headers(access_token),
                json=payload,
            )
            if response.status_code not in [200, 201]:
                logger.error(
                    "Failed to send WhatsApp message",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @whatsapp_circuit_breaker
    async def send_template_message(
        access_token: str,
        phone_number_id: str,
        to: str,
        template_name: str,
        language_code: str = "en_US",
        components: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Sends a pre-approved WhatsApp template message.
        Templates must be created and approved in Meta Business Manager first.
        """
        logger.info(
            "Sending WhatsApp template message", to=to, template=template_name
        )
        template_payload: Dict[str, Any] = {
            "name": template_name,
            "language": {"code": language_code},
        }
        if components:
            template_payload["components"] = components

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": template_payload,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GRAPH_API_BASE}/{phone_number_id}/messages",
                headers=WhatsAppConnector._headers(access_token),
                json=payload,
            )
            if response.status_code not in [200, 201]:
                logger.error(
                    "Failed to send WhatsApp template",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @whatsapp_circuit_breaker
    async def get_message_status(
        access_token: str, message_id: str
    ) -> Dict[str, Any]:
        """
        Retrieves the delivery status of a sent WhatsApp message by its message ID.
        """
        logger.info("Fetching WhatsApp message status", message_id=message_id)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GRAPH_API_BASE}/{message_id}",
                headers=WhatsAppConnector._headers(access_token),
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to get WhatsApp message status",
                    message_id=message_id,
                    status_code=response.status_code,
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @whatsapp_circuit_breaker
    async def mark_as_read(
        access_token: str,
        phone_number_id: str,
        message_id: str,
    ) -> Dict[str, Any]:
        """
        Marks an incoming WhatsApp message as read.
        """
        logger.info("Marking WhatsApp message as read", message_id=message_id)
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GRAPH_API_BASE}/{phone_number_id}/messages",
                headers=WhatsAppConnector._headers(access_token),
                json=payload,
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to mark WhatsApp message as read",
                    message_id=message_id,
                    status_code=response.status_code,
                )
                response.raise_for_status()
            return response.json()
