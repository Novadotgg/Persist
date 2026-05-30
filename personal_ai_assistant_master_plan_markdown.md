# Personal AI Assistant OS — Production-Grade Master Plan

## Vision

Build a unified, resilient, AI-powered personal assistant platform that:
- Connects with multiple apps/services using APIs and MCPs (Model Context Protocol).
- Monitors notifications, emails, and calendar events in real time.
- Prioritizes information intelligently, filtering noise and highlighting critical events.
- Performs semi-autonomous actions (drafting responses, scheduling, task creation) with human-in-the-loop approvals.
- Maintains long-term memory and context via a hybrid SQL + vector database.
- Acts as a local-first, self-hosted personal AI operating system.

### Deployment Targets
- Local-first architecture (minimizing cloud costs and maximizing data privacy).
- Hybrid AI: Local models (Ollama) as the primary engine with optional, encrypted cloud fallbacks (Gemini Free API, Groq).
- Designed for low-latency and graceful degradation when running on local consumer hardware.

---

# 1. High-Level Architecture

```text
               +----------------------------------+
               |          React Frontend          |
               +----------------------------------+
                                || (HTTP / WebSockets / SSE)
                                \/
               +----------------------------------+
               |     FastAPI Backend Gateway      |
               +----------------------------------+
                                ||
        +-----------------------+-----------------------+
        || (Async Tasks)                                || (Read/Write)
        \/                                              \/
+-----------------------+                       +-----------------------+
|  Queue & Jobs Engine  |                       |  PostgreSQL + pgvector|
|  (Dramatiq / Redis)   |                       |  (Relational + Vector)|
+-----------------------+                       +-----------------------+
        ||                                              ||
        \/ (Executes)                                   \/ (Context injection)
+-----------------------+                       +-----------------------+
|  Integration Managers | <===================> |   AI Service Layer    |
| (Gmail, Jira, Calendar|                       | (Local Ollama / Cloud)|
|   via Webhooks/Poll)  |                       +-----------------------+
+-----------------------+                               ||
                                                        \/
                                                +-----------------------+
                                                |  Observability Stack  |
                                                | (Prometheus + Grafana)|
                                                +-----------------------+
```

---

# 2. Production Tech Stack

## Frontend
- **Core**: React.js (Vite), Tailwind CSS (for modern UI styling), Zustand (lightweight global state), React Query (server state synchronization), Axios, React Router.
- **Interactions & Polish**: Framer Motion (micro-animations and transitions), ShadCN UI (component primitives), Socket.io-client / Native WebSockets (for streaming updates).

## Backend
- **Core**: Python 3.11+, FastAPI, Uvicorn, Pydantic v2 (data validation and settings).
- **Database**: PostgreSQL (relational storage) with the `pgvector` extension (semantic embeddings). SQLAlchemy 2.0 (ORM) and Alembic (database schema migrations).
- **Task Queue & Scheduling**: Redis 7.x (broker), Dramatiq (message broker client - selected for simplicity and performance over Celery), APScheduler (cron jobs).
- **AI & Agent Orchestration**: Ollama Python SDK, LangGraph (for multi-agent workflows in Phase 6), OpenAI SDK (compatible with local/cloud endpoints).
- **Logging & Observability**: Structlog (structured JSON logging), Prometheus Client, Grafana.
- **Authentication & Security**: JWT (RS256 asymmetric keys), OAuthlib / Authlib (for Google/Jira OAuth2), Cryptography (Fernet symmetric encryption for credentials).

## Local AI Models
Run locally via Ollama:
- **Tier 1 (Fast Triage)**: `llama3.2:1b` (Fast classification, yes/no routing decisions).
- **Tier 2 (General Reasoning)**: `gpt-oss:20b` (Primary engine for summaries, briefings, chat context).
- **Tier 3 (Complex Agents)**: `qwen2.5:7b` (Optionally pulled for multi-step workflows).

---

# 3. Core Features & Development Phases

## Phase 1 — Foundation & Project Setup
- **App Scaffolding**: Setup backend (FastAPI) and frontend (React + Vite) with Docker orchestration.
- **Database Initializer**: PostgreSQL schema with pgvector enabled, initial user and integration settings tables.
- **Local AI Connection**: Connect to Ollama API. Implement a fallback client layer.
- **Basic Dashboard**: View status of backend, database, queue, and connected Ollama models.

## Phase 2 — Real-Time Event & Queue System
- **Broker Integration**: Initialize Redis + Dramatiq worker queues (`notifications`, `summarization`, `memory`, `integrations`, `scheduler`).
- **Event Schemas**: Rigid Pydantic model enforcing type safety:
  ```python
  class Event(BaseModel):
      id: UUID
      source: str  # e.g., "gmail", "jira"
      type: str    # e.g., "email_received", "ticket_assigned"
      priority: int # 1 (Low) to 5 (Critical)
      payload: dict
      timestamp: datetime
  ```
- **Rule Engine**: Fast, deterministic regex/dictionary-based rule router filtering events before hitting LLM.
- **AI Classification Job**: Tier 1 model (`llama3.2:1b`) identifies urgency, spam status, and routes to appropriate queues.

## Phase 2.5 — Resilience & Error Handling
- **Circuit Breakers**: Implement resilience using standard retry policies for external APIs.
- **Dead Letter Queues (DLQ)**: Failed background tasks are routed to a DLQ after 3 retries rather than silently failing.
- **Idempotency Checks**: De-duplicate incoming events using Redis keys (`event_id:source`) to avoid double processing.
- **Graceful Degradation**: If Ollama goes down, switch to small remote API or queue requests for offline processing without stopping backend servers.

## Phase 3 — Integrations (OAuth2 & Sync)
- **Gmail Integration**: Read inbox messages using OAuth2 PKCE flow, process summaries, check urgency, auto-draft replies.
- **Google Calendar**: Retrieve agendas, detect schedule conflicts, and schedule meeting follow-ups.
- **Jira Integration**: Extract task metadata from conversations/emails and create Jira issues directly.
- **Telegram Bot Integration**: Enable real-time push alerts of high-priority events straight to your phone.

## Phase 4 — Long-Term Memory & RAG Pipeline
- **Memory Pipeline**: Event → Clean Text → Embeddings (via local embedding model) → PostgreSQL `pgvector`.
- **Context Retrieval**: Semantic search fetching relevant user context, preferences, and older projects.
- **Data Lifecycle**: Auto-cleanup job purging raw events after 90 days, keeping semantic summaries for 365 days.

## Phase 5 — Agentic Workflows & Tool Calling
- **Agent Orchestrator**: LangGraph state machine splitting tasks into Planner, Tool Executor, and Memory Updater.
- **Human-in-the-loop (HITL)**: Safe actions (drafting) run automatically; unsafe actions (sending email, deleting tasks) pause for user UI approval.

---

# 4. Extended Directory Structure

```text
backend/
 ├── app/
 │    ├── api/
 │    │    ├── v1/                      # Versioned endpoints
 │    │    │    ├── auth.py
 │    │    │    ├── chat.py
 │    │    │    ├── notifications.py
 │    │    │    ├── integrations.py
 │    │    │    └── settings.py
 │    │    └── deps.py                  # Database and Auth dependencies
 │    ├── core/
 │    │    ├── config.py                # Pydantic Settings (env-based configuration)
 │    │    ├── security.py              # JWT, cryptography, Fernet keys
 │    │    ├── events.py                # App startup/shutdown hooks
 │    │    └── exceptions.py            # Global custom API exceptions
 │    ├── services/
 │    │    ├── ai_service.py            # Ollama API wrapper + cloud fallback
 │    │    ├── email_service.py         # Gmail interactions
 │    │    ├── calendar_service.py      # Google Calendar interactions
 │    │    ├── notification_service.py  # Local & Telegram push
 │    │    └── memory_service.py        # pgvector storage & semantic retrieval
 │    ├── models/                       # SQLAlchemy models
 │    ├── schemas/                      # Pydantic models for validation
 │    ├── agents/                       # LangGraph agent definitions
 │    ├── integrations/
 │    │    ├── base.py                  # Integration abstract base class
 │    │    ├── gmail.py
 │    │    ├── gcal.py
 │    │    ├── jira.py
 │    │    └── telegram.py
 │    ├── workers/                      # Dramatiq task definitions
 │    │    ├── email_worker.py
 │    │    ├── summary_worker.py
 │    │    └── memory_worker.py
 │    ├── middleware/
 │    │    ├── correlation.py           # Structlog tracing correlation IDs
 │    │    ├── rate_limit.py            # Per-IP and user API rate limiting
 │    │    └── logging.py               # Structured HTTP logging middleware
 │    └── main.py
 ├── tests/
 │    ├── unit/                         # Fast Pytest unit tests
 │    ├── integration/                  # Event pipelines and DB integration tests
 │    └── fixtures/                     # Mock data configurations
 ├── alembic/                           # Schema migration files
 ├── Dockerfile
 ├── pyproject.toml                     # Python dependency management (PEP 518)
 └── .env.example
```

---

# 5. Configuration & Environment Management

System variables must be managed centrally via `BaseSettings`:

```python
# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App General Settings
    APP_NAME: str = "Personal AI Assistant OS"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database & Cache Configurations
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"

    # Local AI Configurations
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    PRIMARY_MODEL: str = "gpt-oss:20b"
    FAST_MODEL: str = "llama3.2:1b"
    AI_TIMEOUT_SECONDS: int = 30
    AI_MAX_RETRIES: int = 3

    # Security Configuration
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CREDENTIALS_ENCRYPTION_KEY: str  # Fernet key

    # Third-Party Credentials
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    JIRA_BASE_URL: str = ""
    JIRA_API_TOKEN: str = ""

    # Lifecycle Configs
    EVENT_RETENTION_DAYS: int = 90
    MEMORY_RETENTION_DAYS: int = 365

    class Config:
        env_file = ".env"
        case_sensitive = True
```

---

# 6. Production-Grade Docker Compose

```yaml
version: "3.9"

services:
  frontend:
    build: 
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: dramatiq app.workers
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1.5G

  postgres:
    image: pgvector/pgvector:16-pgdg
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: pa_db
      POSTGRES_USER: pa_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pa_user -d pa_db"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redisdata:/data
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollamadata:/root/.ollama
    ports:
      - "11434:11434"
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]  # Add system GPU support
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafanadata:/var/lib/grafana
    ports:
      - "3001:3000"
    restart: unless-stopped

volumes:
  pgdata:
  redisdata:
  ollamadata:
  grafanadata:
```

---

# 7. Testing & Quality Strategy

## Test Coverage Requirements
- **Unit Tests**: written with `pytest` + `pytest-asyncio`. Run mock verifications on all external endpoints (Ollama API, Google API, Telegram).
- **Integration Tests**: Leverage `Testcontainers` to orchestrate postgres-pgvector and redis in isolation during verification steps.
- **Evaluation Dataset (RAG/Eval)**: 50+ hand-labeled mock messages to evaluate prompt engineering and classification drift over newer local model releases.

---

# 8. Revised Development Timeline

```text
Month 1: Infrastructure, Scaffolding, DB setup, Docker config, and OAuth core.
Month 2: Ollama integration, streaming APIs (SSE), rule-based classification, and Chat UI.
Month 3: Gmail background sync workers, priority detection filters, daily email briefing digest.
Month 4: pgvector schema, semantic chunking pipelines, memory retention jobs, context-augmented search.
Month 5: Google Calendar & Jira OAuth integration, circuit-breakers implementation, and phone pushes (Telegram).
Month 6: LangGraph agents, tool integrations, execution planner, and human-in-the-loop approve UI.
Month 7: Playwright E2E UI verification, Prometheus/Grafana monitors, Tailscale VPN setup, security audit.
```