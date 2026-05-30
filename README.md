# 🌌 Persist — Your **Per**sonal As**sist**ant

[![GitHub license](https://img.shields.io/github/license/Novadotgg/Persist?style=flat-square&color=blue)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Novadotgg/Persist?style=flat-square)](https://github.com/Novadotgg/Persist/stargazers)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB)](https://react.dev)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-000000?style=flat-square)](https://ollama.com)

**Persist** is a highly premium, local-first AI Personal Assistant orchestrating all your daily tools, notes, code, and communications. Powered by local LLMs via Ollama and a FastAPI backend agent, it offers a single, glassmorphic command center to manage your digital life with maximum privacy.

<p align="center">
  <img src="frontend/public/hero-bg.png" width="100%" alt="Persist Interface Mockup" style="border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);" />
</p>

---

## ✨ Features

### 🧠 Local AI Orchestration
*   **Zero-Cloud Privacy:** Runs fully local reasoning models (like `qwen2.5:7b-instruct` or `gemma3`) via Ollama.
*   **Autonomous Agents:** Multi-tool orchestrator that can self-schedule tasks, query databases, control media, and write notes based on natural language commands.

### 🔌 16+ Connected Integrations
Persist wraps the APIs you use daily into clean backend connectors:
*   **Google Workspace:** Gmail (read/draft), Google Calendar (schedule/list), Google Drive (upload/search/download).
*   **Productivity & Planning:** Notion Workspace, Todoist, Atlassian Jira.
*   **Communications:** Slack, Discord, Telegram Bot Alerts, WhatsApp Business Cloud API.
*   **Developer Utilities:** GitHub REST API, local Playwright Browser Scraping & Cloud Browserbase.
*   **Media & Utilities:** Spotify playback control, OpenWeatherMap API, Google Maps Platform, YouTube Data API.

### 💎 Premium User Experience
*   **Cinema-Style Landing Page:** Features a 3D animated loop logo, curvature vector animations, and a moving marquee displaying active integrations.
*   **Glassmorphic Workspace:** Dark-mode dashboard built with Vanilla CSS variables, micro-animations, layout responsiveness, and full-screen expansion.
*   **Live Event Feed:** Real-time push notification stream for background task logs.

---

## 🛠️ Tech Stack

*   **Backend:** Python 3.10+, FastAPI, Uvicorn, SQLite, SQLAlchemy, Pydantic, Prometheus, Playwright.
*   **LLM Inference:** Ollama (local port `11434`).
*   **Frontend:** React 18, Vite, TypeScript, Vanilla CSS (harmonious, tailored HSL colors).
*   **Monitoring:** Prometheus + Grafana metrics export setup.

---

## 📁 Repository Structure

```tree
PA/
├── backend/
│   ├── app/
│   │   ├── agents/          # Orchestrator & tool definitions
│   │   ├── api/             # FastAPI routes (auth, actions, integrations)
│   │   ├── core/            # Config, security, DB session
│   │   └── integrations/    # 16 individual Python connector modules
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── public/              # Brand icons, logo, looping video, hero background
│   ├── src/
│   │   ├── components/      # ChatTerminal, IntegrationsPanel, LandingPage
│   │   └── index.css        # Premium HSL CSS design tokens
│   ├── package.json
│   └── vite.config.ts
├── .gitignore
├── QUICKSTART.md
└── USER_MANUAL.md
```

---

## 🚀 Getting Started

### Prerequisites

1.  **Ollama:** Install Ollama from [ollama.com](https://ollama.com).
2.  **Pull LLM Model:**
    ```bash
    ollama pull qwen2.5:7b-instruct
    ```
3.  **Python 3.10+** and **Node.js 18+**.

---

### Backend Setup

1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```
2.  Create and activate virtual environment:
    ```bash
    python -m venv venv
    # Windows:
    .\venv\Scripts\activate
    # macOS/Linux:
    source venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Configure environment variables:
    ```bash
    cp .env.example .env
    # Fill in your database URL and API keys in the generated .env
    ```
5.  Start backend server:
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```

---

### Frontend Setup

1.  Navigate to the frontend directory:
    ```bash
    cd ../frontend
    ```
2.  Install packages:
    ```bash
    npm install
    ```
3.  Launch the development server:
    ```bash
    npm run dev
    ```
4.  Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## ⚙️ Configuration & Secrets

Secrets are configured via `backend/.env` (which is kept out of Git by the root `.gitignore`).

For integrations such as Spotify, Notion, or WhatsApp Business, simply input your tokens/credentials directly inside the **Connected Integrations** panel on the frontend, or pre-populate the environment keys in the backend configurations.

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
