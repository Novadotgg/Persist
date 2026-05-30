import pytest
import base64
import httpx
from unittest.mock import MagicMock, patch, AsyncMock
from app.core.security import encrypt_token, decrypt_token
from app.integrations.gmail import GmailConnector
from app.integrations.gcal import GoogleCalendarConnector
from app.integrations.jira import JiraConnector
from app.integrations.telegram import TelegramConnector

# ==========================================
# 1. SECURITY / CRYPTOGRAPHY TESTS
# ==========================================

def test_token_encryption_decryption():
    """
    Test that encrypting and decrypting credential tokens roundtrips correctly.
    """
    original_token = "ya29.a0AcwsB0..."
    
    encrypted = encrypt_token(original_token)
    assert encrypted != original_token
    assert len(encrypted) > 0
    
    decrypted = decrypt_token(encrypted)
    assert decrypted == original_token


# ==========================================
# 2. GMAIL CONNECTOR TESTS
# ==========================================

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_gmail_exchange_auth_code(mock_post):
    """
    Verify Gmail OAuth authorization code exchange endpoint payload and response parsing.
    """
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "access_token": "mock-access-token",
        "refresh_token": "mock-refresh-token",
        "expires_in": 3600
    }
    mock_post.return_value = mock_res

    tokens = await GmailConnector.exchange_auth_code(
        code="auth-code-123",
        code_verifier="verifier-456",
        redirect_uri="http://localhost:8000/callback"
    )
    
    assert tokens["access_token"] == "mock-access-token"
    assert tokens["refresh_token"] == "mock-refresh-token"
    mock_post.assert_called_once()


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_gmail_fetch_unread_messages(mock_get):
    """
    Verify Gmail fetch unread messages lists endpoint mapping.
    """
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "messages": [
            {"id": "msg-1", "threadId": "thread-1"},
            {"id": "msg-2", "threadId": "thread-2"}
        ]
    }
    mock_get.return_value = mock_res

    messages = await GmailConnector.fetch_unread_messages(access_token="mock-token", max_results=5)
    
    assert len(messages) == 2
    assert messages[0]["id"] == "msg-1"
    mock_get.assert_called_once()


def test_gmail_parse_payload():
    """
    Verify parsing utility extracts header items correctly from Google response payloads.
    """
    msg_detail = {
        "id": "msg-12345",
        "snippet": "Test email body snippet",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Project Outage Warning!"},
                {"name": "From", "value": "boss@company.com"}
            ]
        }
    }
    
    parsed = GmailConnector.parse_message_payload(msg_detail)
    
    assert parsed["id"] == "msg-12345"
    assert parsed["sender"] == "boss@company.com"
    assert parsed["subject"] == "Project Outage Warning!"
    assert parsed["body"] == "Test email body snippet"


# ==========================================
# 3. GOOGLE CALENDAR CONNECTOR TESTS
# ==========================================

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_gcal_fetch_upcoming_events(mock_get):
    """
    Verify calendar events query parsing.
    """
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "items": [
            {
                "id": "event-1",
                "summary": "Outage Retrospective Meeting",
                "start": {"dateTime": "2026-05-26T15:00:00Z"},
                "end": {"dateTime": "2026-05-26T16:00:00Z"}
            }
        ]
    }
    mock_get.return_value = mock_res

    events = await GoogleCalendarConnector.fetch_upcoming_events(access_token="mock-token")
    
    assert len(events) == 1
    assert events[0]["summary"] == "Outage Retrospective Meeting"
    mock_get.assert_called_once()


# ==========================================
# 4. JIRA CONNECTOR TESTS
# ==========================================

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_jira_create_issue(mock_post):
    """
    Verify Jira issue creation Basic Auth encoding and ADF formatting.
    """
    mock_res = MagicMock()
    mock_res.status_code = 201
    mock_res.json.return_value = {
        "id": "10001",
        "key": "KAN-12",
        "self": "https://jira.com/issue/10001"
    }
    mock_post.return_value = mock_res

    # Provide explicit credentials for testing
    res = await JiraConnector.create_issue(
        project_key="KAN",
        summary="Fix database issue",
        description="Fix the critical index problem.",
        base_url="https://test-jira.atlassian.net",
        api_token="testuser@company.com:my-api-token"
    )

    assert res["key"] == "KAN-12"
    
    # Assert headers included correct base64 encoded token
    headers_arg = mock_post.call_args[1]["headers"]
    expected_encoded = base64.b64encode("testuser@company.com:my-api-token".encode()).decode()
    assert headers_arg["Authorization"] == f"Basic {expected_encoded}"


# ==========================================
# 5. TELEGRAM CONNECTOR TESTS
# ==========================================

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_telegram_send_alert(mock_post):
    """
    Verify Telegram Bot messaging request formatting.
    """
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {"ok": True, "result": {"message_id": 99}}
    mock_post.return_value = mock_res

    res = await TelegramConnector.send_alert(
        bot_token="123456:bottoken",
        chat_id="987654321",
        text="Test message text"
    )

    assert res["ok"] is True
    mock_post.assert_called_once()
    
    # Assert request payload was correct
    payload_arg = mock_post.call_args[1]["json"]
    assert payload_arg["chat_id"] == "987654321"
    assert payload_arg["text"] == "Test message text"
