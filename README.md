# FinPath — AI-Powered Behavioral Wealth Architect

> An autonomous **Personal CFO** powered by multi-agent AI that bridges the gap between daily spending and generational wealth.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)
![Groq](https://img.shields.io/badge/AI-Groq%20%2B%20Ollama-orange?logo=openai)
![RAG](https://img.shields.io/badge/RAG-ChromaDB%208.6K%20chunks-purple)

---

## ✨ What is FinPath?

FinPath is an **AI-powered personal financial advisor** that combines real-time behavioral analysis of your spending with intelligent goal modeling, portfolio recommendations, and real-time decision nudges — all using a multi-agent architecture with explainable AI.

**Key Differentiators:**
- 🧠 **12 specialized AI agents** working in concert (not a single chatbot)
- 📊 **Behavioral spending analysis** — detects "leakage patterns" (subscriptions, impulse buys)
- 🎯 **Goal-aware nudging** — "This ₹500 Swiggy order delays your house goal by 1 day"
- 🔍 **Full explainability** — every AI decision has an audit trail with reasoning chains and RAG sources
- 🇮🇳 **India-native** — ₹ formatting, SIP/ELSS/PPF/NPS context, Indian tax optimization (80C/80D)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (Port 3000)              │
│      Vanilla JS SPA + Express Proxy → Backend       │
├─────────────────────────────────────────────────────┤
│                   Backend (Port 8000)               │
│              FastAPI + 21 REST Endpoints            │
├──────────┬──────────┬──────────┬────────────────────┤
│Behavioral│   Goal   │  Nudge   │   CFO Chat Agent   │
│  Agent   │  Agent   │  Agent   │   (Conversational)  │
├──────────┼──────────┼──────────┼────────────────────┤
│Portfolio │   Tax    │Retirement│ Statement Analysis  │
│  Agent   │  Agent   │  Agent   │      Agent          │
├──────────┼──────────┼──────────┼────────────────────┤
│ Macro    │Sentiment │  Graph   │  Document Intel     │
│ Agent    │  Agent   │  Agent   │      Agent          │
├──────────┴──────────┴──────────┴────────────────────┤
│              Shared Infrastructure                   │
│  Groq/Ollama LLM │ ChromaDB RAG │ Hallucination Guard│
│  Memory Agent    │ Audit Logger │ INR Enforcer       │
└─────────────────────────────────────────────────────┘
```

### AI Agents (12)

| # | Agent | What It Does |
|---|-------|-------------|
| 1 | **Behavioral Analysis** | Categorizes transactions, identifies spending leakages |
| 2 | **Goal Modeling** | Inflation-adjusted goal planning with daily savings targets |
| 3 | **Intelligent Portfolio** | Risk-based asset allocation (Equity/Debt/Gold) |
| 4 | **Nudge & Alert** | Real-time purchase impact analysis ("Delays goal by X days") |
| 5 | **CFO Chat** | Conversational AI with full profile context |
| 6 | **Tax Optimizer** | Old vs New regime comparison, 80C/80D recommendations |
| 7 | **Retirement Planner** | NPS/EPF projections to age 60 with generational wealth |
| 8 | **Statement Analysis** | DCF valuation, variance analysis, peer comparables |
| 9 | **Macro Climate** | RBI repo rate signals and allocation adjustments |
| 10 | **Market Sentiment** | News-based sector sentiment scoring |
| 11 | **Graph Agent** | Knowledge graph queries (Neo4j, with RAG fallback) |
| 12 | **Document Intelligence** | PDF/XLSX upload, text extraction, RAG indexing |

### Supporting Infrastructure

| Component | Purpose |
|-----------|---------|
| **Groq (Primary)** | Llama 3.3 70B — fast cloud inference for nudge/chat |
| **Ollama (Fallback)** | Qwen2.5 7B — local model when Groq unavailable |
| **ChromaDB RAG** | 8,663 knowledge chunks from Indian finance corpus |
| **Hallucination Guard** | Validates all LLM outputs before delivery |
| **INR Enforcer** | Central system prompt ensuring ₹ formatting globally |
| **Memory Agent** | Session-scoped decision logging for audit trails |
| **MCP Server** | Model Context Protocol for IDE/assistant integration |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- Ollama (optional, for local fallback)
- Groq API Key (free tier works)

### 1. Clone & Setup

```bash
git clone <repo-url>
cd cbit

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r finpath/backend/requirements.txt

# Install frontend dependencies
cd finpath/frontend && npm install && cd ../..
```

### 2. Configure Environment

```bash
cp finpath/backend/.env.example finpath/backend/.env
# Edit .env and set your GROQ_API_KEY
```

**Key .env settings:**

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | (required) | Your Groq API key |
| `FAST_DEMO_MODE` | `1` | `1` = instant computed responses, `0` = full LLM for all agents |
| `PRIMARY_MODEL_PROVIDER` | `groq` | `groq` or `ollama` |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Cloud model |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Local fallback model |

### 3. Start the Application

```bash
# Terminal 1: Backend
cd finpath/backend
source ../../venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd finpath/frontend
node server.js
```

### 4. Open the Dashboard

Navigate to **http://localhost:3000** in your browser.

---

## 🧪 Demo Script (Recommended Order)

### Step 1 — Load Priya's Profile (Dashboard)
Fill the **Live Demo Inputs** form:
- Name: `Priya Sharma`, Age: `28`, City: `Hyderabad`
- Income: `60000`, Fixed Expenses: `18000`
- Goal: `Buy a house in Hyderabad`, Amount: `1500000`, Years: `5`
- Risk: `Moderate`
- Paste transactions CSV → Click **Apply Live Inputs**

### Step 2 — CFO Chat
Ask: `Can I afford a vacation to Goa in December if I save ₹2,000 less this month?`
- AI references Priya's surplus, calculates exact impact on house timeline

### Step 3 — Nudge Simulator (⭐ Demo Moment)
- Amount: `500`, Item: `Swiggy dinner order` → **"Goal Delayed by 1 Day — Proceed"**
- Amount: `50000`, Item: `iPhone 16 Pro` → **"Goal Delayed by 43 Days — Reconsider"**

---

## 📡 API Endpoints (21)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/demo/context` | Set session profile + transactions |
| `GET` | `/demo/context/{id}` | Get session context |
| `GET` | `/analyze` | Behavioral spending analysis |
| `GET` | `/goal` | Goal feasibility & modeling |
| `GET` | `/portfolio` | Asset allocation recommendations |
| `POST` | `/nudge` | Purchase impact analysis |
| `POST` | `/chat` | CFO conversational AI |
| `POST` | `/analyze/statement` | Financial statement DCF analysis |
| `GET` | `/portfolio/live` | Live robo-advisor allocation |
| `POST` | `/documents/upload` | Document intelligence (PDF/XLSX) |
| `POST` | `/graph/query` | Knowledge graph query |
| `GET` | `/news/sentiment` | Market sentiment analysis |
| `GET` | `/tax/optimize` | Tax regime optimization |
| `POST` | `/report/monthly` | Monthly financial report (PDF) |
| `GET` | `/retirement/plan` | NPS/EPF retirement projection |
| `GET` | `/macro/climate` | Macro economic climate signal |
| `GET` | `/audit/{session_id}` | Audit trail for session |
| `POST` | `/rag/query` | RAG knowledge base query |
| `POST` | `/rag/upsert` | Add document to RAG |
| `GET` | `/rag/stats` | RAG collection statistics |

---

## 📁 Project Structure

```
cbit/
├── hackathon_master_plan.md       # Project source of truth
├── README.md                      # This file
├── finpath/
│   ├── backend/
│   │   ├── main.py                # FastAPI app + 21 endpoints
│   │   ├── .env                   # Configuration
│   │   ├── agents/
│   │   │   ├── behavioral_agent.py
│   │   │   ├── goal_agent.py
│   │   │   ├── nudge_agent.py
│   │   │   ├── cfo_chat_agent.py
│   │   │   ├── portfolio_agent.py
│   │   │   ├── tax_agent.py
│   │   │   ├── retirement_agent.py
│   │   │   ├── financial_statement_agent.py
│   │   │   ├── macro_agent.py
│   │   │   ├── sentiment_agent.py
│   │   │   ├── graph_agent.py
│   │   │   ├── document_intelligence_agent.py
│   │   │   ├── ollama_helper.py   # LLM routing + INR enforcement
│   │   │   ├── hallucination_guard.py
│   │   │   ├── memory_agent.py    # Session decision logging
│   │   │   └── audit.py           # Audit trail builder
│   │   ├── rag/
│   │   │   ├── rag_engine.py      # ChromaDB vector store
│   │   │   └── india_finance_knowledge.txt
│   │   └── default_profile.json
│   ├── frontend/
│   │   ├── server.js              # Express + proxy to backend
│   │   └── public/
│   │       ├── index.html         # SPA shell
│   │       ├── css/index.css      # Design system
│   │       ├── js/
│   │       │   ├── app.js         # Main application logic
│   │       │   ├── api.js         # API client layer
│   │       │   └── nudge.js       # Nudge modal logic
│   │       └── pages/             # HTML page templates
│   └── mcp_server/                # Model Context Protocol server
└── finpath_data/
    └── data/chroma_db/            # Persistent vector store
```

---

## ⚡ Performance

With `FAST_DEMO_MODE=1`:

| Endpoint | Response Time |
|----------|:---:|
| Health check | 7ms |
| Spending analysis | 29ms |
| Goal modeling | 13ms |
| Tax optimization | 8ms |
| Statement analysis | 11ms |
| Nudge (with LLM) | 3-8s |
| CFO Chat (with LLM) | 5-12s |

---

## 🔒 Explainability & Audit

Every AI decision includes:
- **Confidence Level** — high / medium / low
- **Hallucination Guard** — PASSED / FLAGGED
- **Reasoning Chain** — numbered steps explaining the logic
- **RAG Sources** — which knowledge documents were consulted
- **Session Audit Trail** — complete timeline at `/audit/{session_id}`

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **Frontend** | Vanilla JS, Express.js, CSS3 |
| **AI (Cloud)** | Groq — Llama 3.3 70B Versatile |
| **AI (Local)** | Ollama — Qwen2.5 7B |
| **RAG** | ChromaDB + all-MiniLM-L6-v2 embeddings |
| **Reports** | ReportLab (PDF generation) |
| **MCP** | Model Context Protocol for IDE integration |

---

## 📝 License

Built for **Hackathon PS 7** — AI-Powered Behavioral Wealth Architect.

---

*Built with ❤️ by Team FinPath*
