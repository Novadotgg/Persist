# Personal AI Assistant OS — End-to-End Next Steps Roadmap

This roadmap details the code design, system requirements, and implementation guides for developers to build out the remaining phases of the platform, building directly on the Phase 1 setup.

---

## Phase 2: Event System & Queue Processing

To build a high-performance system that handles incoming emails, tasks, and calendar events without lagging the web server, we use a message queue (Dramatiq) backed by Redis.

```text
Incoming Event (API Webhook or Sync Poller)
   │
   ▼
FastAPI Router (Validates schema & logs request)
   │
   ▼
[Redis Queue]
   │
   ▼
Dramatiq Worker Pipeline
   ├── Task 1: Classify priority (llama3.2:1b)
   ├── Task 2: Summarize details (gpt-oss)
   └── Task 3: Store in SQL database and generate memory embeddings
```

### 1. Dramatiq Setup Example
Add worker setup code in `backend/app/workers/__init__.py`:

```python
import dramatiq
from dramatiq.brokers.redis import RedisBroker
from app.core.config import settings

# Configure Redis as the broker channel
redis_broker = RedisBroker(url=settings.REDIS_URL)
dramatiq.set_broker(redis_broker)
```

### 2. Event Worker Code (`backend/app/workers/event_worker.py`)
```python
import dramatiq
import httpx
import structlog
from app.core.config import settings

logger = structlog.get_logger()

@dramatiq.actor(queue_name="notifications", max_retries=3)
def process_incoming_event(event_data: dict):
    """
    Background job triggered on incoming message/email.
    Performs AI classification and schedules summarization.
    """
    event_id = event_data.get("id")
    source = event_data.get("source")
    logger.info("Processing event background task", event_id=event_id, source=source)
    
    # 1. AI triage call to Tier 1 model (Llama 3.2 1B)
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.FAST_MODEL,
                    "prompt": f"Classify priority (high/medium/low) for: {event_data.get('payload')}. Respond with ONLY the label.",
                    "stream": False
                }
            )
            priority = response.json().get("response", "low").strip().lower()
            logger.info("AI triage complete", event_id=event_id, priority=priority)
            
            # 2. Schedule summary job if priority is medium or high
            if priority in ["high", "medium"]:
                dramatiq.enqueue("summarization", args=[event_data])
    except Exception as e:
        logger.error("Failed event triage classification", event_id=event_id, error=str(e))
        raise
```

---

## Phase 2.5: Resilience & Error Handling

To make the platform robust enough for production usage, implement retry policies, circuit breakers, and idempotency states.

### 1. Circuit Breaker for External APIs
When Gmail or Jira APIs rate-limit or fail, the system must not exhaust worker slots waiting for timeouts. Implement a circuit breaker wrapping integrations:

```python
# app/integrations/base.py
import time
import structlog

logger = structlog.get_logger()

class CircuitBreakerOpenException(Exception):
    pass

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.last_state_change = time.time()

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if time.time() - self.last_state_change > self.recovery_timeout:
                    self.state = "HALF-OPEN"
                    logger.info("Circuit transition to HALF-OPEN", function=func.__name__)
                else:
                    raise CircuitBreakerOpenException(f"Circuit open for {func.__name__}")
            try:
                result = func(*args, **kwargs)
                if self.state == "HALF-OPEN":
                    self.state = "CLOSED"
                    self.failure_count = 0
                    logger.info("Circuit closed successfully", function=func.__name__)
                return result
            except Exception as e:
                self.failure_count += 1
                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"
                    self.last_state_change = time.time()
                    logger.error("Circuit opened due to failures", function=func.__name__, failures=self.failure_count)
                raise e
        return wrapper
```

### 2. Event Idempotency & Dedup (in Redis)
Ensure an incoming email isn't parsed multiple times:
```python
# app/middleware/idempotency.py
from redis import Redis
from app.core.config import settings

redis_client = Redis.from_url(settings.REDIS_URL)

def is_duplicate_event(event_id: str, expiration_seconds: int = 86400) -> bool:
    """
    Returns True if the event has been processed in the last 24h.
    """
    key = f"processed_event:{event_id}"
    is_new = redis_client.set(key, "1", ex=expiration_seconds, nx=True)
    return not is_new
```

---

## Phase 3: Integration Connectors

The core integrations bridge the assistant to email, tasks, and mobile channels.

### 1. Gmail PKCE OAuth Adaptor (`backend/app/integrations/gmail.py`)
Configure Google OAuth PKCE parameters to retrieve access and refresh tokens. Safe-store refresh tokens using Cryptography Fernet encryption in PostgreSQL:

```python
from cryptography.fernet import Fernet
from app.core.config import settings

fernet = Fernet(settings.CREDENTIALS_ENCRYPTION_KEY.encode())

def encrypt_token(token: str) -> str:
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(token_hash: str) -> str:
    return fernet.decrypt(token_hash.encode()).decode()
```

### 2. Google Calendar Poller
Runs on a 5-minute cron trigger (`APScheduler` job):
- Query Google Calendar event updates.
- Parse description text for meetings context.
- Identify date conflicts and create task cards for resolution.

### 3. Telegram Alerts
To push alerts to your phone, implement a simple webhook wrapper using the Telegram Bot API:
```python
import httpx

async def send_telegram_alert(chat_id: str, bot_token: str, text: str):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)
```

---

## Phase 4: Semantic Memory System (RAG)

Context memory utilizes PostgreSQL with `pgvector` to run semantic text searches locally.

### 1. Migration Setup (SQLAlchemy + pgvector)
Configure `app/models/memory.py`:
```python
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()

class Memory(Base):
    __tablename__ = "memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    # 768 or 1024 or 384 dimensions depending on chosen local Ollama embedding model
    embedding = Column(Vector(768)) 
    tags = Column(JSON, default=dict)
    importance = Column(Integer, default=1)
    created_at = Column(DateTime, nullable=False)
```

### 2. Embeddings Generation Helper (`backend/app/services/memory_service.py`)
```python
import httpx
from app.core.config import settings

async def generate_local_embedding(text: str) -> list[float]:
    """
    Generates embedding vectors via local Ollama endpoint (e.g., using 'nomic-embed-text' model)
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/embeddings",
            json={
                "model": "nomic-embed-text",
                "prompt": text
            }
        )
        return response.json().get("embedding", [])
```

---

## Phase 5: LangGraph Agent reasoning

For complex planning (e.g. "Schedule a follow-up with John and prepare task list on Jira"), we build a multi-node agent.

```text
       +-----------------+
       |  User Prompt    |
       +-----------------+
                │
                ▼
       +-----------------+
       |  Planner Agent  | ◄──── Loop Node
       +-----------------+
                │
                ├───────────────┐
                ▼               ▼
        [Call Gmail API]  [Call Jira API]
                │               │
                └───────┬───────┘
                        ▼
               +-----------------+
               |  Memory Updater |
               +-----------------+
                        │
                        ▼
               +-----------------+
               |  Final Response |
               +-----------------+
```

### 1. Human-in-the-Loop Approval State
All modifications must go through approval states. Add checking tables for actions awaiting review:
```python
class ActionApproval(Base):
    __tablename__ = "action_approvals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration = Column(String, nullable=False)  # "gmail", "jira"
    action_type = Column(String, nullable=False)  # "send_email", "create_ticket"
    payload = Column(JSON, nullable=False)        # email content or ticket JSON
    status = Column(String, default="PENDING")    # PENDING, APPROVED, REJECTED
```

---

## Phase 6: Frontend UX Polish

Add state variables to the React app to display notification priorities and real-time events.

### 1. Real-Time Streaming Notifications Component
Create `frontend/src/components/NotificationFeed.tsx`:
```tsx
import { useState, useEffect } from 'react'

interface Notification {
  id: string
  source: string
  title: string
  summary: string
  priority: number
  timestamp: string
}

export function NotificationFeed() {
  const [notifications, setNotifications] = useState<Notification[]>([])

  useEffect(() => {
    // SSE Stream endpoint from FastAPI
    const sse = new EventSource('http://localhost:8000/api/v1/notifications/stream')

    sse.onmessage = (event) => {
      const data = JSON.parse(event.data)
      setNotifications((prev) => [data, ...prev].slice(0, 50))
    }

    return () => {
      sse.close()
    }
  }, [])

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
      <h3 className="font-semibold text-slate-200">Live Notifications</h3>
      <div className="space-y-3 divide-y divide-slate-800 max-h-96 overflow-y-auto">
        {notifications.map((n) => (
          <div key={n.id} className="pt-3 flex justify-between gap-4">
            <div>
              <span className={`text-[10px] px-2 py-0.5 rounded font-mono ${
                n.priority >= 4 ? 'bg-red-500/10 text-red-400' : 'bg-slate-800 text-slate-400'
              }`}>
                {n.source}
              </span>
              <p className="text-sm font-medium text-slate-300 mt-1">{n.title}</p>
              <p className="text-xs text-slate-500 mt-0.5">{n.summary}</p>
            </div>
            <span className="text-[10px] text-slate-600 font-mono">
              {new Date(n.timestamp).toLocaleTimeString()}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
```

---

## Phase 7: Observability & Production Verification

Verify execution states, monitor latencies, and alert on system bottlenecks.

### 1. Scrape Targets
Ensure Prometheus monitors backend API route request latencies and active DB pool connections. Key metrics to monitor:
- `http_requests_total`: Request volumes.
- `ai_generation_latency_seconds`: Local model execution times.
- `dramatiq_queue_depth`: Task processing bottlenecks.

### 2. E2E Validation Command
Verify complete docker-compose environment setup matches specifications:
```bash
docker compose exec backend pytest tests/
```
