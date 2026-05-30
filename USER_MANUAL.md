# 📖 Personal AI Assistant OS — User Manual

> Your intelligent, local-first AI companion that monitors your Gmail, Google Calendar, Jira, and Telegram — and lets you chat with an AI agent that actually knows your context.

---

## Table of Contents

1. [What is Personal AI Assistant OS?](#1-what-is-personal-ai-assistant-os)
2. [Accessing the App](#2-accessing-the-app)
3. [Dashboard Overview](#3-dashboard-overview)
4. [AI Chat Terminal](#4-ai-chat-terminal)
5. [Integrations Panel](#5-integrations-panel)
6. [Live Notification Feed](#6-live-notification-feed)
7. [Infrastructure Status](#7-infrastructure-status)
8. [API Documentation](#8-api-documentation)
9. [Telegram Notifications](#9-telegram-notifications)
10. [Tips & Best Practices](#10-tips--best-practices)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. What is Personal AI Assistant OS?

Personal AI Assistant OS is a **self-hosted AI agent** that:

- 🧠 **Thinks and reasons** using a local AI model (Ollama) — your data never leaves your machine
- 📧 **Monitors Gmail** — reads, classifies, and summarizes your emails automatically
- 📅 **Tracks Google Calendar** — fetches upcoming events and reminds you
- 🎫 **Manages Jira** — creates issues and tracks tasks on your behalf
- 📲 **Sends Telegram alerts** — pushes important notifications straight to your phone
- 💾 **Remembers context** — stores conversations in semantic memory so it learns your preferences over time

---

## 2. Accessing the App

Make sure Docker Desktop is running, then open:

| Service | URL | Description |
|---|---|---|
| 🖥️ **Main Dashboard** | http://localhost:3000 | The main UI |
| 📖 **API Explorer** | http://localhost:8000/api/v1/docs | Interactive API docs |
| 📊 **Grafana Metrics** | http://localhost:3001 | System observability |

> **Default Grafana credentials:** username `admin`, password `admin`

---

## 3. Dashboard Overview

When you open http://localhost:3000 you'll see:

```
┌─────────────────────────────────────────────────────┐
│  PA  Personal AI Assistant OS          System Online │  ← Header
├─────────────────────────────────────────────────────┤
│  Welcome Banner + "Explore API Docs" button          │  ← Hero Section
├─────────────────────────────────────────────────────┤
│  Connected Integrations (Google | Telegram | Jira)   │  ← Integrations Panel
├──────────────────────────┬──────────────────────────┤
│                          │  Live Notification Feed   │
│   AI Chat Terminal       ├──────────────────────────┤
│                          │  Infrastructure Status    │
└──────────────────────────┴──────────────────────────┘
```

---

## 4. AI Chat Terminal

The **Chat Terminal** is your main way to interact with the AI agent.

### How to use it

1. Click the text input at the bottom of the terminal
2. Type your request in plain English
3. Press **Enter** or click **Send**
4. Watch the status indicator change:
   - 🟡 `PLANNING` — the AI is thinking about what to do
   - 🔵 `EXECUTING` — the AI is running tasks
   - 🟢 `COMPLETED` — response ready
   - 🔴 `ERROR` — something went wrong

### Example queries you can ask

| Query | What the AI does |
|---|---|
| `"Summarize my unread emails"` | Fetches and summarizes Gmail inbox |
| `"What meetings do I have today?"` | Pulls Google Calendar events |
| `"Create a Jira task to fix the login bug"` | Creates a Jira issue |
| `"Send a Telegram message: standup in 10 mins"` | Sends alert to your Telegram |
| `"What did I work on last week?"` | Searches your semantic memory |
| `"Remind me about the project deadline"` | Stores a memory for later retrieval |

### Reasoning Trace

After each response, the AI shows a **reasoning trace** — a step-by-step log of how it reached the answer (classify → plan → execute → respond). This gives you full transparency into what the AI is doing.

---

## 5. Integrations Panel

The integrations panel shows the status of all your connected services. Each integration must be set up once before it starts working.

---

### 🔵 Google Suite (Gmail + Calendar)

This connects your Gmail inbox and Google Calendar so the AI can read emails and fetch your schedule.

#### Step 1 — Create a Google Cloud Project & OAuth credentials

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click **"Select a project"** → **"New Project"** → name it (e.g. `Personal AI Assistant`) → **Create**
3. Go to **APIs & Services → Library**
4. Search **"Gmail API"** → click it → **Enable**
5. Search **"Google Calendar API"** → click it → **Enable**
6. Go to **APIs & Services → OAuth consent screen**
   - User type: **External** → **Create**
   - App name: `Passist` (or any name)
   - Support email: your Gmail address
   - Click **Save and Continue** through all steps
7. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
   - Application type: **Web application**
   - Under **Authorized redirect URIs** → click **Add URI** → paste:
     ```
     http://localhost:8000/api/v1/integrations/google/callback
     ```
   - Click **Create**
8. Copy the **Client ID** and **Client Secret** into your `.env`:
   ```
   GOOGLE_CLIENT_ID="xxxx.apps.googleusercontent.com"
   GOOGLE_CLIENT_SECRET="GOCSPX-xxxx"
   ```

#### Step 2 — Add test users (required while app is in Testing mode)

Your app starts in **Testing** mode — only approved accounts can sign in.

1. Go to **APIs & Services → OAuth consent screen**
2. Scroll to **"Test users"** section
3. Click **"+ Add Users"**
4. Add every Gmail address that should be able to connect (e.g. `yourname@gmail.com`)
5. Click **Save**

> **Note:** You only need to do this while your app is unverified. For a personal app, Testing mode is perfectly fine — just add all accounts you use.

#### Step 3 — Connect in the app

1. Open http://localhost:3000
2. In the **Connected Integrations** panel, click **Connect Account** under **Google OAuth**
3. You'll be redirected to Google's login page
4. Select the Gmail account you added as a test user
5. Click **Allow** to grant Gmail and Calendar read access
6. You'll be redirected back to the dashboard — the integration is now active ✅

Once connected, the system **automatically syncs every 5 minutes**:
- 📧 New Gmail messages are classified and summarized
- 📅 Upcoming calendar events are fetched and stored

---

### 🤖 Telegram

Telegram is used to receive push notifications on your phone for important events.

#### Step 1 — Create a Telegram Bot

1. Open the **Telegram** app on your phone or desktop
2. Search for **@BotFather** and start a chat
3. Send the command: `/newbot`
4. Enter a display name (e.g. `My PA Bot`)
5. Enter a username ending in `bot` (e.g. `mypa_assistant_bot`)
6. BotFather replies with your **bot token**:
   ```
   123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
   ```
7. Copy this into your `.env`:
   ```
   TELEGRAM_BOT_TOKEN="123456789:ABCdef..."
   ```

#### Step 2 — Get your Chat ID

1. Search for your new bot in Telegram (e.g. `@mypa_assistant_bot`)
2. Send it any message (e.g. `hello`)
3. Open this URL in your browser (replace `<TOKEN>` with your bot token):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
4. In the JSON response, look for:
   ```json
   "chat": { "id": 123456789 }
   ```
5. Copy that number into your `.env`:
   ```
   TELEGRAM_CHAT_ID="123456789"
   ```

#### Step 3 — Apply and verify

Restart the backend after updating `.env`:
```powershell
docker compose up -d --build backend worker
```

The bot will now send you real-time alerts. **No action needed in the app UI** — Telegram works fully in the background.

---

### 🟦 Jira

Connects Jira so the AI can create and manage issues on your behalf.

#### Step 1 — Get your Jira API Token

1. Go to [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **Create API token**
3. Give it a label (e.g. `Personal AI Assistant`)
4. Click **Create** → copy the token immediately (it won't be shown again)

#### Step 2 — Find your Jira workspace URL

Your Jira base URL is the domain you use to access Jira:
```
https://your-company.atlassian.net
```
> If you go to Jira in your browser, the URL in the address bar is your base URL (e.g. `https://sayan.atlassian.net`)

#### Step 3 — Add to `.env`

```
JIRA_BASE_URL="https://your-domain.atlassian.net"
JIRA_API_TOKEN="ATATTxxxx"
```

Then restart:
```powershell
docker compose up -d --build backend worker
```

Once configured, you can ask the AI things like:
- *"Create a Jira bug: login page crashes on mobile"*
- *"Add a task to the PA project: set up CI/CD pipeline"*

---

## 6. Live Notification Feed

The **Notification Feed** (right panel) shows real-time alerts streamed from the backend via SSE (Server-Sent Events).

### Notification types

| Type | Icon | Description |
|---|---|---|
| **Email** | 📧 | New important Gmail message detected |
| **Calendar** | 📅 | Upcoming meeting alert |
| **Jira** | 🎫 | Issue status change |
| **System** | ⚙️ | Background task updates |

### Filtering

Use the tabs at the top of the feed to filter by type:
- **All** — shows everything
- **Email** — Gmail notifications only
- **Calendar** — meeting alerts only

Notifications are also sent to your **Telegram** in real time.

---

## 7. Infrastructure Status

The bottom-right panel shows the live health of your backend services:

| Service | What it does |
|---|---|
| **PostgreSQL Database** | Stores events, memories, integrations |
| **Redis & Dramatiq Workers** | Handles background task processing |
| **Ollama AI Connection** | Runs the local AI model |

- 🟢 **Green pulse** = healthy
- 🟡 **Yellow** = degraded
- 🔴 **Red** = offline

---

## 8. API Documentation

The full REST API is available at **http://localhost:8000/api/v1/docs**

Key endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/health` | GET | System health check |
| `/api/v1/agent/chat` | POST | Send a message to the AI agent |
| `/api/v1/memory/search` | GET | Search semantic memory |
| `/api/v1/integrations/google/connect` | GET | Start Google OAuth flow |
| `/api/v1/integrations/jira/connect` | POST | Connect Jira |
| `/api/v1/notifications/stream` | GET | SSE notification stream |
| `/api/v1/metrics` | GET | Prometheus metrics |

---

## 9. Telegram Notifications

Your Telegram bot (`@Trickster0pbot`) automatically sends alerts for:

- 📧 High-priority emails (from VIPs, with urgent keywords)
- 📅 Calendar events starting in the next 30 minutes
- ✅ Completed background tasks
- ⚠️ System errors or warnings

**You don't need to do anything** — notifications are sent automatically as the background worker processes events.

---

## 10. Tips & Best Practices

### Getting the best AI responses
- Be specific: *"Summarize emails from John about the Q3 project"* works better than *"check emails"*
- The AI remembers past conversations — reference them: *"Like the task you helped me with yesterday..."*
- For actions (creating Jira issues, sending Telegram messages), the AI will ask for your approval before executing

### Human-in-the-Loop (HITL)
For sensitive actions (sending messages, creating issues), the AI will pause and ask:
> *"I'm about to create a Jira issue titled 'Fix login bug' in project PA. Should I proceed?"*

Reply **yes** to confirm or **no** to cancel.

### Data Privacy
- All AI processing runs **locally** on your machine via Ollama
- Your emails and calendar data are processed locally — nothing is sent to external AI services unless you configure a fallback provider (OpenAI/Gemini) in `.env`
- Memories are stored encrypted in your own Supabase database

---

## 11. Troubleshooting

### Dashboard shows "Failed to connect to backend"
```
→ Make sure Docker is running: docker compose ps
→ Check backend logs: docker compose logs backend
```

### AI responses are slow or timing out
```
→ The Ollama model may still be loading. Wait 1-2 minutes after startup.
→ Check: docker compose exec ollama ollama list
```

### Notifications not appearing
```
→ Check Redis is running: docker compose ps redis
→ Check worker logs: docker compose logs worker
```

### Google integration not connecting
```
→ Make sure your redirect URI in Google Cloud Console is:
  http://localhost:8000/api/v1/integrations/google/callback
→ Check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env
```

### Telegram bot not sending messages
```
→ Verify TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env
→ Send a message to @Trickster0pbot in Telegram to activate the chat
```

### Full restart
```powershell
docker compose down
docker compose up -d
```

---

*Personal AI Assistant OS — Built with local-first security principles. Your data stays yours.*
