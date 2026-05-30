import secrets
import hashlib
import base64
import structlog
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.core.security import encrypt_token, decrypt_token
from app.db.session import get_db
from app.models.models import User, Integration
from app.integrations.gmail import GmailConnector
from app.integrations.jira import JiraConnector
from app.integrations.telegram import TelegramConnector
from app.integrations.notion import NotionConnector
from app.integrations.todoist import TodoistConnector
from app.integrations.weather import WeatherConnector
from app.integrations.github_integration import GitHubConnector
from app.integrations.discord import DiscordConnector
from app.integrations.slack import SlackConnector
from app.middleware.idempotency import redis_client
from app.services.scheduler import sync_gmail_job, sync_gcal_job
from app.api.deps import get_current_user

logger = structlog.get_logger()
router = APIRouter()

# ─── Schema Definitions ───────────────────────────────────────────────────────

class IntegrationStatusResponse(BaseModel):
    provider: str
    is_active: bool
    created_at: str

class TestTelegramRequest(BaseModel):
    bot_token: str
    chat_id: str

class SaveTelegramRequest(BaseModel):
    bot_token: str
    chat_id: str

class SaveJiraRequest(BaseModel):
    base_url: str
    api_token: str

class TestJiraRequest(BaseModel):
    project_key: str
    summary: str
    description: str
    base_url: Optional[str] = None
    api_token: Optional[str] = None

# New integration schemas
class SaveApiTokenRequest(BaseModel):
    """Generic schema for integrations that use a single API token."""
    api_token: str

class SaveSpotifyRequest(BaseModel):
    client_id: str
    client_secret: str

class SaveWhatsAppRequest(BaseModel):
    access_token: str
    phone_number_id: str

class SaveGoogleMapsRequest(BaseModel):
    api_key: str

class SaveWeatherRequest(BaseModel):
    api_key: str

class SaveYouTubeRequest(BaseModel):
    api_key: str

class SaveGitHubRequest(BaseModel):
    personal_access_token: str

class SaveDiscordRequest(BaseModel):
    bot_token: str

class SaveSlackRequest(BaseModel):
    bot_token: str

class SaveBrowserbaseRequest(BaseModel):
    api_key: str
    project_id: str

class TestNotionRequest(BaseModel):
    api_token: str
    query: Optional[str] = "test"

class TestTodoistRequest(BaseModel):
    api_token: str

class TestWeatherRequest(BaseModel):
    api_key: str
    city: str = "London"

class TestGitHubRequest(BaseModel):
    personal_access_token: str

class TestDiscordRequest(BaseModel):
    bot_token: str
    channel_id: str
    message: str = "✅ Personal AI Assistant OS — Discord integration test successful!"

class TestSlackRequest(BaseModel):
    bot_token: str
    channel: str
    message: str = "✅ Personal AI Assistant OS — Slack integration test successful!"

# ─── Helper Functions ──────────────────────────────────────────────────────────

def _generate_challenge(verifier: str) -> str:
    """Generate SHA-256 code challenge for PKCE."""
    sha = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(sha).decode("utf-8").replace("=", "")
    return challenge


async def _save_integration_credentials(
    db: AsyncSession,
    user_id: uuid.UUID,
    provider: str,
    credentials: Dict[str, Any],
) -> Integration:
    """
    Upserts an Integration record for the given user and provider.
    Merges new credentials into existing ones.
    """
    query = select(Integration).where(
        Integration.user_id == user_id,
        Integration.provider == provider,
    )
    result = await db.execute(query)
    integration = result.scalar_one_or_none()

    if not integration:
        integration = Integration(
            user_id=user_id,
            provider=provider,
            is_active=True,
        )
        db.add(integration)

    existing = dict(integration.credentials) if integration.credentials else {}
    existing.update(credentials)
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()
    integration.credentials = existing
    integration.is_active = True
    await db.commit()
    return integration


# ─── Existing Endpoints ────────────────────────────────────────────────────────

@router.get("/config")
async def get_integration_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns saved integration credentials from Database or fallback to .env settings.
    Credentials from DB are decrypted before being returned.
    """
    telegram_bot_token = settings.TELEGRAM_BOT_TOKEN or ""
    telegram_chat_id = settings.TELEGRAM_CHAT_ID or ""
    jira_base_url = settings.JIRA_BASE_URL or ""

    # Fetch Telegram integration from DB
    telegram_query = select(Integration).where(
        Integration.user_id == current_user.id,
        Integration.provider == "telegram",
        Integration.is_active == True
    )
    res_tg = await db.execute(telegram_query)
    tg_integration = res_tg.scalar_one_or_none()
    if tg_integration and tg_integration.credentials:
        dec_token = decrypt_token(tg_integration.credentials.get("bot_token", ""))
        dec_chat = decrypt_token(tg_integration.credentials.get("chat_id", ""))
        if dec_token:
            telegram_bot_token = dec_token
        if dec_chat:
            telegram_chat_id = dec_chat

    # Fetch Jira integration from DB
    jira_query = select(Integration).where(
        Integration.user_id == current_user.id,
        Integration.provider == "jira",
        Integration.is_active == True
    )
    res_jira = await db.execute(jira_query)
    jira_integration = res_jira.scalar_one_or_none()
    if jira_integration and jira_integration.credentials:
        dec_url = jira_integration.credentials.get("base_url", "")
        if dec_url:
            jira_base_url = dec_url

    # Helper to check if a provider is configured in DB
    async def _is_configured(provider: str) -> bool:
        q = select(Integration).where(
            Integration.user_id == current_user.id,
            Integration.provider == provider,
            Integration.is_active == True,
        )
        res = await db.execute(q)
        return res.scalar_one_or_none() is not None

    return {
        "telegram": {
            "bot_token": telegram_bot_token,
            "chat_id": telegram_chat_id,
            "configured": bool(telegram_bot_token and telegram_chat_id),
        },
        "jira": {
            "base_url": jira_base_url,
            "configured": bool(
                jira_integration is not None
                or (
                    settings.JIRA_API_TOKEN
                    and settings.JIRA_API_TOKEN != "your_jira_api_token_here"
                )
            ),
        },
        # New integrations — boolean configured flags only (no secret leakage)
        "notion": {"configured": await _is_configured("notion") or bool(settings.NOTION_API_TOKEN)},
        "todoist": {"configured": await _is_configured("todoist") or bool(settings.TODOIST_API_TOKEN)},
        "spotify": {"configured": await _is_configured("spotify") or bool(settings.SPOTIFY_CLIENT_ID)},
        "whatsapp": {"configured": await _is_configured("whatsapp") or bool(settings.WHATSAPP_ACCESS_TOKEN)},
        "google_maps": {"configured": await _is_configured("google_maps") or bool(settings.GOOGLE_MAPS_API_KEY)},
        "weather": {"configured": await _is_configured("weather") or bool(settings.OPENWEATHERMAP_API_KEY)},
        "youtube": {"configured": await _is_configured("youtube") or bool(settings.YOUTUBE_API_KEY)},
        "github": {"configured": await _is_configured("github") or bool(settings.GITHUB_PAT)},
        "discord": {"configured": await _is_configured("discord") or bool(settings.DISCORD_BOT_TOKEN)},
        "slack": {"configured": await _is_configured("slack") or bool(settings.SLACK_BOT_TOKEN)},
        "browser": {"configured": await _is_configured("browser")},
    }


@router.post("/telegram")
async def save_telegram(
    request: SaveTelegramRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Saves Telegram Bot credentials encrypted in the database."""
    logger.info("Saving Telegram integration credentials", user_id=str(current_user.id))
    encrypted_token = encrypt_token(request.bot_token)
    encrypted_chat = encrypt_token(request.chat_id)
    await _save_integration_credentials(
        db, current_user.id, "telegram",
        {"bot_token": encrypted_token, "chat_id": encrypted_chat},
    )
    return {"status": "success", "message": "Telegram credentials saved successfully."}


@router.post("/jira")
async def save_jira(
    request: SaveJiraRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Saves Jira integration credentials encrypted in the database."""
    logger.info("Saving Jira integration credentials", user_id=str(current_user.id))
    encrypted_token = encrypt_token(request.api_token)
    await _save_integration_credentials(
        db, current_user.id, "jira",
        {"base_url": request.base_url, "api_token": encrypted_token},
    )
    return {"status": "success", "message": "Jira credentials saved successfully."}


@router.get("/google/login")
async def google_login(current_user: User = Depends(get_current_user)):
    """Generates Google OAuth2 authorization redirect URL using PKCE."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=400,
            detail="GOOGLE_CLIENT_ID is not configured in settings.",
        )
    code_verifier = secrets.token_urlsafe(64)
    state = secrets.token_urlsafe(16)
    code_challenge = _generate_challenge(code_verifier)

    if redis_client:
        try:
            redis_client.set(f"oauth:verifier:{state}", code_verifier, ex=600)
            redis_client.set(f"oauth:state_user:{state}", str(current_user.id), ex=600)
        except Exception as e:
            logger.error("Failed to save OAuth session info to Redis", error=str(e))
            raise HTTPException(status_code=500, detail="OAuth session store unreachable.")
    else:
        logger.warning("Redis offline during OAuth login, cannot store state securely.")

    redirect_uri = "http://localhost:8000/api/v1/integrations/google/callback"
    # Include Drive scope in addition to Gmail and Calendar
    scopes = (
        "https://www.googleapis.com/auth/gmail.readonly "
        "https://www.googleapis.com/auth/calendar.readonly "
        "https://www.googleapis.com/auth/drive.readonly"
    )
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        f"&scope={scopes}"
        f"&state={state}"
        f"&code_challenge={code_challenge}"
        "&code_challenge_method=S256"
        "&access_type=offline"
        "&prompt=consent"
    )
    return {"url": auth_url, "state": state}


@router.get("/google/callback")
async def google_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    """OAuth2 Redirect Callback. Exchanges auth code for tokens and saves them in DB."""
    if not redis_client:
        raise HTTPException(status_code=500, detail="Session store offline.")

    code_verifier = redis_client.get(f"oauth:verifier:{state}")
    user_id_str = redis_client.get(f"oauth:state_user:{state}")

    if not code_verifier or not user_id_str:
        raise HTTPException(
            status_code=400,
            detail="OAuth session has expired or state is invalid.",
        )
    redis_client.delete(f"oauth:verifier:{state}")
    redis_client.delete(f"oauth:state_user:{state}")

    user_uuid = uuid.UUID(user_id_str.decode())
    redirect_uri = "http://localhost:8000/api/v1/integrations/google/callback"
    try:
        token_response = await GmailConnector.exchange_auth_code(
            code=code,
            code_verifier=code_verifier.decode(),
            redirect_uri=redirect_uri,
        )
    except Exception as e:
        logger.error("Token exchange failed", error=str(e))
        raise HTTPException(status_code=400, detail="Failed to retrieve tokens from Google.")

    refresh_token = token_response.get("refresh_token")
    access_token = token_response.get("access_token")
    encrypted_refresh = encrypt_token(refresh_token) if refresh_token else ""
    encrypted_access = encrypt_token(access_token) if access_token else ""

    creds: Dict[str, Any] = {}
    if encrypted_refresh:
        creds["refresh_token"] = encrypted_refresh
    creds["access_token"] = encrypted_access
    await _save_integration_credentials(db, user_uuid, "google", creds)

    logger.info("Successfully connected Google integration", user_id=str(user_uuid))
    return Response(
        content="Google Integration connected successfully! You can close this window now.",
        media_type="text/html",
    )


@router.get("", response_model=List[IntegrationStatusResponse])
async def list_integrations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns all active integrations for the current user."""
    query = select(Integration).where(Integration.user_id == current_user.id)
    result = await db.execute(query)
    integrations = result.scalars().all()
    db_integrations = {i.provider: i for i in integrations}
    response_list = []

    # Known providers to enumerate with settings fallback
    provider_settings_fallbacks = {
        "telegram": bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID),
        "jira": bool(
            settings.JIRA_API_TOKEN
            and settings.JIRA_API_TOKEN != "your_jira_api_token_here"
        ),
        "notion": bool(settings.NOTION_API_TOKEN),
        "todoist": bool(settings.TODOIST_API_TOKEN),
        "spotify": bool(settings.SPOTIFY_CLIENT_ID),
        "whatsapp": bool(settings.WHATSAPP_ACCESS_TOKEN),
        "google_maps": bool(settings.GOOGLE_MAPS_API_KEY),
        "weather": bool(settings.OPENWEATHERMAP_API_KEY),
        "youtube": bool(settings.YOUTUBE_API_KEY),
        "github": bool(settings.GITHUB_PAT),
        "discord": bool(settings.DISCORD_BOT_TOKEN),
        "slack": bool(settings.SLACK_BOT_TOKEN),
    }

    # Add DB integrations (Google, all new providers saved in DB)
    for provider, integration in db_integrations.items():
        response_list.append(IntegrationStatusResponse(
            provider=provider,
            is_active=integration.is_active,
            created_at=integration.created_at.isoformat() if integration.created_at else "",
        ))

    # Add settings-only configured integrations not already in DB
    db_providers = set(db_integrations.keys())
    for provider, is_fallback_configured in provider_settings_fallbacks.items():
        if provider not in db_providers and is_fallback_configured:
            response_list.append(IntegrationStatusResponse(
                provider=provider,
                is_active=True,
                created_at="",
            ))

    return response_list


@router.post("/sync")
async def trigger_manual_sync(current_user: User = Depends(get_current_user)):
    """Manually triggers background sync tasks for Gmail and Google Calendar."""
    logger.info("Manual sync triggered via API", user_id=str(current_user.id))
    try:
        await sync_gmail_job()
        await sync_gcal_job()
        return {"status": "success", "message": "Sync jobs executed successfully."}
    except Exception as e:
        logger.error("Manual sync failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Manual sync failed: {str(e)}")


# ─── Original Test Endpoints ──────────────────────────────────────────────────

@router.post("/test/telegram")
async def test_telegram(request: TestTelegramRequest, current_user: User = Depends(get_current_user)):
    """Triggers a test notification push message using user provided Telegram Bot details."""
    text = (
        "🔔 *Personal AI Assistant OS*\n\n"
        "This is a test alert! Your Telegram push integration is configured successfully."
    )
    try:
        res = await TelegramConnector.send_alert(
            bot_token=request.bot_token,
            chat_id=request.chat_id,
            text=text,
        )
        return {"status": "success", "response": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Telegram test failed: {str(e)}")


@router.post("/test/jira")
async def test_jira(request: TestJiraRequest, current_user: User = Depends(get_current_user)):
    """Triggers creation of a test issue in Jira using project details."""
    try:
        res = await JiraConnector.create_issue(
            project_key=request.project_key,
            summary=request.summary,
            description=request.description,
            base_url=request.base_url,
            api_token=request.api_token,
        )
        return {"status": "success", "response": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Jira test failed: {str(e)}")


# ─── New Save Endpoints ────────────────────────────────────────────────────────

@router.post("/notion")
async def save_notion(
    request: SaveApiTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Saves Notion integration API token encrypted in the database."""
    logger.info("Saving Notion credentials", user_id=str(current_user.id))
    await _save_integration_credentials(
        db, current_user.id, "notion",
        {"api_token": encrypt_token(request.api_token)},
    )
    return {"status": "success", "message": "Notion credentials saved successfully."}


@router.post("/todoist")
async def save_todoist(
    request: SaveApiTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Saves Todoist API token encrypted in the database."""
    logger.info("Saving Todoist credentials", user_id=str(current_user.id))
    await _save_integration_credentials(
        db, current_user.id, "todoist",
        {"api_token": encrypt_token(request.api_token)},
    )
    return {"status": "success", "message": "Todoist credentials saved successfully."}


@router.post("/spotify")
async def save_spotify(
    request: SaveSpotifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Saves Spotify OAuth2 app credentials encrypted in the database."""
    logger.info("Saving Spotify credentials", user_id=str(current_user.id))
    await _save_integration_credentials(
        db, current_user.id, "spotify",
        {
            "client_id": encrypt_token(request.client_id),
            "client_secret": encrypt_token(request.client_secret),
        },
    )
    return {"status": "success", "message": "Spotify credentials saved successfully."}


@router.post("/whatsapp")
async def save_whatsapp(
    request: SaveWhatsAppRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Saves WhatsApp Business API credentials encrypted in the database."""
    logger.info("Saving WhatsApp credentials", user_id=str(current_user.id))
    await _save_integration_credentials(
        db, current_user.id, "whatsapp",
        {
            "access_token": encrypt_token(request.access_token),
            "phone_number_id": request.phone_number_id,
        },
    )
    return {"status": "success", "message": "WhatsApp credentials saved successfully."}


@router.post("/google_maps")
async def save_google_maps(
    request: SaveGoogleMapsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Saves Google Maps API key encrypted in the database."""
    logger.info("Saving Google Maps credentials", user_id=str(current_user.id))
    await _save_integration_credentials(
        db, current_user.id, "google_maps",
        {"api_key": encrypt_token(request.api_key)},
    )
    return {"status": "success", "message": "Google Maps credentials saved successfully."}


@router.post("/weather")
async def save_weather(
    request: SaveWeatherRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Saves OpenWeatherMap API key encrypted in the database."""
    logger.info("Saving Weather credentials", user_id=str(current_user.id))
    await _save_integration_credentials(
        db, current_user.id, "weather",
        {"api_key": encrypt_token(request.api_key)},
    )
    return {"status": "success", "message": "Weather API credentials saved successfully."}


@router.post("/youtube")
async def save_youtube(
    request: SaveYouTubeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Saves YouTube Data API key encrypted in the database."""
    logger.info("Saving YouTube credentials", user_id=str(current_user.id))
    await _save_integration_credentials(
        db, current_user.id, "youtube",
        {"api_key": encrypt_token(request.api_key)},
    )
    return {"status": "success", "message": "YouTube credentials saved successfully."}


@router.post("/github")
async def save_github(
    request: SaveGitHubRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Saves GitHub Personal Access Token encrypted in the database."""
    logger.info("Saving GitHub credentials", user_id=str(current_user.id))
    await _save_integration_credentials(
        db, current_user.id, "github",
        {"pat": encrypt_token(request.personal_access_token)},
    )
    return {"status": "success", "message": "GitHub credentials saved successfully."}


@router.post("/discord")
async def save_discord(
    request: SaveDiscordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Saves Discord Bot token encrypted in the database."""
    logger.info("Saving Discord credentials", user_id=str(current_user.id))
    await _save_integration_credentials(
        db, current_user.id, "discord",
        {"bot_token": encrypt_token(request.bot_token)},
    )
    return {"status": "success", "message": "Discord credentials saved successfully."}


@router.post("/slack")
async def save_slack(
    request: SaveSlackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Saves Slack Bot token encrypted in the database."""
    logger.info("Saving Slack credentials", user_id=str(current_user.id))
    await _save_integration_credentials(
        db, current_user.id, "slack",
        {"bot_token": encrypt_token(request.bot_token)},
    )
    return {"status": "success", "message": "Slack credentials saved successfully."}


@router.post("/browser")
async def save_browser(
    request: SaveBrowserbaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Saves Browserbase cloud credentials for remote browser automation."""
    logger.info("Saving Browserbase credentials", user_id=str(current_user.id))
    await _save_integration_credentials(
        db, current_user.id, "browser",
        {
            "api_key": encrypt_token(request.api_key),
            "project_id": request.project_id,
        },
    )
    return {"status": "success", "message": "Browserbase credentials saved successfully."}


# ─── New Test Endpoints ────────────────────────────────────────────────────────

@router.post("/test/notion")
async def test_notion(request: TestNotionRequest, current_user: User = Depends(get_current_user)):
    """Tests Notion integration by searching for pages."""
    try:
        results = await NotionConnector.search_pages(
            api_token=request.api_token,
            query=request.query or "",
            max_results=3,
        )
        return {
            "status": "success",
            "message": f"Notion connected. Found {len(results)} results.",
            "results_count": len(results),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Notion test failed: {str(e)}")


@router.post("/test/todoist")
async def test_todoist(request: TestTodoistRequest, current_user: User = Depends(get_current_user)):
    """Tests Todoist integration by fetching projects."""
    try:
        projects = await TodoistConnector.get_projects(api_token=request.api_token)
        return {
            "status": "success",
            "message": f"Todoist connected. Found {len(projects)} project(s).",
            "projects_count": len(projects),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Todoist test failed: {str(e)}")


@router.post("/test/weather")
async def test_weather(request: TestWeatherRequest, current_user: User = Depends(get_current_user)):
    """Tests OpenWeatherMap integration by fetching current weather for a city."""
    try:
        data = await WeatherConnector.get_current_weather(
            api_key=request.api_key,
            city=request.city,
        )
        parsed = WeatherConnector.parse_current_weather(data)
        return {
            "status": "success",
            "message": f"Weather API connected. {parsed['city']}: {parsed['condition']}, {parsed['temperature']}°C.",
            "weather": parsed,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Weather API test failed: {str(e)}")


@router.post("/test/github")
async def test_github(request: TestGitHubRequest, current_user: User = Depends(get_current_user)):
    """Tests GitHub integration by fetching the authenticated user profile."""
    try:
        user = await GitHubConnector.get_authenticated_user(pat=request.personal_access_token)
        return {
            "status": "success",
            "message": f"GitHub connected as @{user.get('login', 'unknown')}.",
            "user": {
                "login": user.get("login"),
                "name": user.get("name"),
                "public_repos": user.get("public_repos"),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"GitHub test failed: {str(e)}")


@router.post("/test/discord")
async def test_discord(request: TestDiscordRequest, current_user: User = Depends(get_current_user)):
    """Tests Discord integration by sending a message to a channel."""
    try:
        result = await DiscordConnector.send_message(
            bot_token=request.bot_token,
            channel_id=request.channel_id,
            content=request.message,
        )
        return {
            "status": "success",
            "message": "Discord message sent successfully.",
            "message_id": result.get("id"),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Discord test failed: {str(e)}")


@router.post("/test/slack")
async def test_slack(request: TestSlackRequest, current_user: User = Depends(get_current_user)):
    """Tests Slack integration by posting a message to a channel."""
    try:
        result = await SlackConnector.post_message(
            bot_token=request.bot_token,
            channel=request.channel,
            text=request.message,
        )
        return {
            "status": "success",
            "message": "Slack message sent successfully.",
            "ts": result.get("ts"),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Slack test failed: {str(e)}")
