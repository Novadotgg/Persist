# 🤖 Personal AI Assistant OS — Quick Start Guide

## Every Time You Open the App

### 1. Start Docker Desktop
Make sure **Docker Desktop** is running before anything else.

---

### 2. Start All Services
Open a terminal in `C:\Users\sayan\OneDrive\Desktop\PA` and run:

```powershell
docker compose up -d
```

Wait ~30–60 seconds for everything to start. Check status with:

```powershell
docker compose ps
```

All services should show **running** or **healthy**.

---

### 3. Open the App

| Service | URL |
|---|---|
| 🖥️ **Frontend Dashboard** | http://localhost:3000 |
| 📖 **API Docs (Swagger)** | http://localhost:8000/api/v1/docs |
| 📊 **Grafana Dashboards** | http://localhost:3001 (admin / admin) |
| 🔍 **Prometheus Metrics** | http://localhost:9090 |

---

### 4. Stop Everything (when done)

```powershell
docker compose down
```

---

## First Time Only (One-Time Setup)

These steps only need to be done **once** after cloning the project.

### A. Copy the environment file
```powershell
Copy-Item backend\.env .env
```

### B. Initialize the database
```powershell
docker compose exec backend python -m app.db.init_db
```

### C. Pull the Ollama AI model (~3GB download)
```powershell
docker compose exec ollama ollama pull gpt-oss:20b
docker compose exec ollama ollama pull llama3.2:1b
```

---

## Troubleshooting

### A service won't start?
Check its logs:
```powershell
docker compose logs backend
docker compose logs worker
docker compose logs postgres
docker compose logs redis
```

### Backend crashed / database error?
Restart just the backend:
```powershell
docker compose restart backend
```

### AI responses not working?
Make sure the Ollama model is downloaded:
```powershell
docker compose exec ollama ollama list
```
If empty, re-run the model pull from the first-time setup.

### Full reset (nuclear option)
```powershell
docker compose down -v   # removes all data volumes
docker compose up -d
# then redo first-time setup steps B and C
```

---

## Development Mode (without Docker)

If you want hot-reload during development, run services locally:

**Terminal 1 — Backend API**
```powershell
cd backend
..\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Dramatiq Worker**
```powershell
cd backend
..\venv\Scripts\Activate.ps1
dramatiq app.workers
```

**Terminal 3 — Frontend**
```powershell
cd frontend
npm run dev   # opens at http://localhost:5173
```

> **Note:** In local dev mode, Redis must be running locally. The `.env` file already points to `localhost:6379`.

---

## Running Tests

```powershell
# Backend (31 tests)
cd backend
python -m pytest tests/ -v

# Frontend E2E (Playwright)
cd frontend
npx playwright install   # first time only
npx playwright test
```
