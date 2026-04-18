# FinPath Code Base (Current State)

This file documents the current code base under `/home/harini/cbit/finpath`.

## 1) Repository Layout

```text
/home/harini/cbit/finpath/
├── backend/
├── frontend/
└── mcp_server/
```

## 2) Backend (`finpath/backend`)

### 2.1 Core API
- `main.py`
  - FastAPI app entrypoint
  - Session-based demo context storage (`SESSION_CONTEXTS`)
  - Transaction CSV write path: `memory/demo_inputs/`
  - Default seed files:
    - `default_profile.json`
    - `default_transactions.csv`
  - Exposes health, analysis, goal, portfolio, nudge, chat, statement, report, tax, retirement, macro, sentiment, audit, memory, and RAG endpoints.

### 2.2 Agents (`finpath/backend/agents`)
- `behavioral_agent.py` - spending categorization + leakage insights
- `goal_agent.py` - target/inflation/required savings and feasibility
- `portfolio_agent.py` - static allocation recommendation
- `robo_advisor_agent.py` - live/fallback allocation and rebalance hints
- `nudge_agent.py` - purchase impact + delay estimation
- `cfo_chat_agent.py` - conversational CFO response generation
- `tax_agent.py` - tax suggestions and savings optimization
- `retirement_agent.py` - retirement corpus projection
- `macro_agent.py` - macro climate signal and tilt suggestions
- `sentiment_agent.py` - market headline sentiment summary
- `financial_statement_agent.py` - statement analysis outputs
- `document_intelligence_agent.py` - uploaded document extraction/analysis
- `graph_agent.py` - graph query with fallback reasoning
- `report_agent.py` - monthly report orchestration
- `memory_agent.py` - event persistence/load helpers
- `audit.py` - standardized reasoning/audit payload builder
- `hallucination_guard.py` - guard wrapper for output text
- `ollama_helper.py` - model invocation bridge

### 2.3 RAG Layer (`finpath/backend/rag`)
- `rag_engine.py` - ChromaDB query/upsert engine
- `init_rag.py` - RAG setup helpers
- `india_finance_knowledge.txt` - base knowledge corpus

### 2.4 Runtime Data
- `memory/agent_memory.json` - stored decision events
- `memory/chat_sessions/*.json` - per-session chat history
- `memory/demo_inputs/*_transactions.csv` - session transaction files
- `reports/` - generated PDF and model evaluation reports

### 2.5 Environment
- `.env` and `.env.example`
- Current model path config includes:
  - `PRIMARY_MODEL_PROVIDER=groq`
  - Groq model/API settings
  - Ollama fallback settings
  - `FAST_DEMO_MODE=0` (full model/RAG path enabled)

## 3) Frontend (`finpath/frontend`)

### 3.1 Server
- `server.js` - static serving + `/api/*` proxy to backend
- `package.json`, `package-lock.json`

### 3.2 App Shell
- `public/index.html` - shell, sidebar navigation, page mount

### 3.3 Main SPA Logic (`public/js`)
- `app.js`
  - route/page loader
  - dashboard live input form handling
  - apply-live flow to `/api/demo/context`
  - dashboard analytics rendering from backend endpoints
  - current gating: dashboard insights render only after Apply in current run
- `api.js` - frontend API wrappers
- `audit.js` - reasoning/audit collapsible render
- `nudge.js` - nudge overlay/modal behavior
- `charts.js` - chart rendering wrappers
- `typewriter.js` - streaming/typewriter UI effect

### 3.4 Pages (`public/pages`)
- `dashboard.html`
- `spending.html`
- `goal.html`
- `portfolio.html`
- `nudge.html`
- `cfo-chat.html`
- `tax.html`
- `sentiment.html`
- `retirement.html`
- `macro.html`
- `documents.html`
- `statement.html`
- `audit-trail.html`

### 3.5 Styles (`public/css`)
- `design-system.css`
- `layout.css`
- `components.css`
- `charts.css`
- `animations.css`

## 4) MCP Server (`finpath/mcp_server`)

### 4.1 Entry and Config
- `finpath_mcp_server.py` - MCP server runtime
- `start_mcp.sh` - convenience launcher
- `mcp_config.json` - MCP config manifest
- `claude_desktop_config.json` - desktop integration sample
- `README.md`

### 4.2 Tools (`finpath/mcp_server/tools`)
- `behavioral_tools.py`
- `goal_tools.py`
- `portfolio_tools.py`
- `nudge_tools.py`
- `cfo_tools.py`
- `tax_tools.py`
- `sentiment_tools.py`
- `retirement_tools.py`
- `document_tools.py`
- `audit_tools.py`
- `memory_tools.py`
- `rag_tools.py`
- `rag_coordinator_tools.py`
- `browser_tools.py`
- `__init__.py`

### 4.3 MCP Resources/Prompts
- `resources/finpath_resources.py`
- `prompts/finpath_prompts.py`

## 5) Current Behavior Notes

- Frontend is connected to backend through `frontend/server.js` proxy (`/api/*`).
- Dashboard live context is session-scoped and updated via Apply.
- Backend derives `existing_savings` from:
  - monthly income
  - monthly fixed expenses
  - sum of transaction amounts
- CFO chat is bullet-formatted and includes audit metadata with RAG source IDs when available.
- MCP server startup path is valid after browser tool syntax fix.

## 6) Run Commands (Typical)

### Backend
```bash
cd /home/harini/cbit
source venv/bin/activate
cd finpath/backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd /home/harini/cbit/finpath/frontend
npm start
```

### MCP Server
```bash
cd /home/harini/cbit
source venv/bin/activate
cd finpath/mcp_server
python finpath_mcp_server.py
```

---

Last updated: 2026-04-18
