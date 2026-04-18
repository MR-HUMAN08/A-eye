from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents import memory_agent
from agents.behavioral_agent import analyze_transactions
from agents.cfo_chat_agent import chat
from agents.document_intelligence_agent import process_upload
from agents.financial_statement_agent import analyze_statement
from agents.goal_agent import calculate_goal_plan
from agents.graph_agent import query_graph
from agents.macro_agent import macro_climate
from agents.nudge_agent import evaluate_purchase
from agents.portfolio_agent import recommend_portfolio
from agents.report_agent import generate_monthly_report
from agents.retirement_agent import retirement_plan
from agents.robo_advisor_agent import live_portfolio
from agents.sentiment_agent import analyze_news_sentiment
from agents.tax_agent import optimize_tax
from rag.rag_engine import engine as rag_engine


BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")

app = FastAPI(title="FinPath Backend", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROFILE_PATH = BASE / "default_profile.json"
TX_PATH = BASE / "default_transactions.csv"
DEMO_INPUT_DIR = BASE / "memory" / "demo_inputs"
DEMO_INPUT_DIR.mkdir(parents=True, exist_ok=True)

SESSION_CONTEXTS: dict[str, dict[str, Any]] = {}


def load_profile() -> dict[str, Any]:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


class NudgeRequest(BaseModel):
    amount: float
    description: str
    session_id: str | None = None


class ChatRequest(BaseModel):
    message: str
    session_id: str


class StatementRequest(BaseModel):
    financial_data: dict[str, list[float]]
    company_name: str
    period: str
    planned: list[float] | None = None


class GraphRequest(BaseModel):
    query: str
    session_id: str


class RAGQueryRequest(BaseModel):
    question: str
    top_k: int = 5


class RAGUpsertRequest(BaseModel):
    text: str
    metadata: dict[str, Any] | None = None


class DemoContextRequest(BaseModel):
    session_id: str
    profile: dict[str, Any]
    transactions: list[dict[str, Any]]


def _session_profile_and_tx(session_id: str | None) -> tuple[dict[str, Any], str]:
    if session_id and session_id in SESSION_CONTEXTS:
        ctx = SESSION_CONTEXTS[session_id]
        return dict(ctx["profile"]), str(ctx["tx_path"])
    return load_profile(), str(TX_PATH)


def _write_session_transactions(session_id: str, transactions: list[dict[str, Any]]) -> str:
    tx_path = DEMO_INPUT_DIR / f"{session_id}_transactions.csv"
    required = {"date", "description", "category", "amount"}
    if not transactions:
        frame = pd.DataFrame(columns=["date", "description", "category", "amount"])
    else:
        frame = pd.DataFrame(transactions)
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"transactions missing required columns: {sorted(missing)}")
    frame = frame[["date", "description", "category", "amount"]].copy()
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce").fillna(0.0)
    frame.to_csv(tx_path, index=False)
    return str(tx_path)


@app.get("/")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "finpath-backend", "explainable_ai": True}


@app.post("/demo/context")
def demo_context(payload: DemoContextRequest) -> dict[str, Any]:
    """Set dynamic demo context (profile + transactions) for a session."""
    profile = dict(payload.profile)
    try:
        tx_path = _write_session_transactions(payload.session_id, payload.transactions)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Keep profile savings aligned with current live inputs and transactions.
    monthly_income = float(profile.get("monthly_income", 0) or 0)
    monthly_fixed = float(profile.get("monthly_fixed_expenses", 0) or 0)
    monthly_variable = sum(float((tx or {}).get("amount", 0) or 0) for tx in payload.transactions)
    profile["existing_savings"] = max(0.0, monthly_income - monthly_fixed - monthly_variable)

    SESSION_CONTEXTS[payload.session_id] = {
        "profile": profile,
        "tx_path": tx_path,
    }
    return {
        "status": "ok",
        "session_id": payload.session_id,
        "profile_name": profile.get("name", "User"),
        "transactions": len(payload.transactions),
    }


@app.get("/demo/context/{session_id}")
def get_demo_context(session_id: str) -> dict[str, Any]:
    ctx = SESSION_CONTEXTS.get(session_id)
    if not ctx:
        return {"status": "not_found", "session_id": session_id}
    frame = pd.read_csv(ctx["tx_path"])
    return {
        "status": "ok",
        "session_id": session_id,
        "profile": ctx["profile"],
        "transactions": frame.to_dict(orient="records"),
    }


@app.get("/analyze")
def analyze(session_id: str | None = None) -> dict[str, Any]:
    sid = session_id or str(uuid.uuid4())
    profile, tx_path = _session_profile_and_tx(sid)
    return analyze_transactions(tx_path, sid, profile)


@app.get("/goal")
def goal(session_id: str | None = None) -> dict[str, Any]:
    sid = session_id or str(uuid.uuid4())
    profile, tx_path = _session_profile_and_tx(sid)
    monthly_variable = float(pd.read_csv(tx_path)["amount"].sum())
    return calculate_goal_plan(profile, monthly_variable, sid)


@app.get("/portfolio")
def portfolio(session_id: str | None = None) -> dict[str, Any]:
    sid = session_id or str(uuid.uuid4())
    profile, tx_path = _session_profile_and_tx(sid)
    monthly_variable = float(pd.read_csv(tx_path)["amount"].sum())
    g = calculate_goal_plan(profile, monthly_variable, sid)
    return recommend_portfolio(profile, g, sid)


@app.post("/nudge")
def nudge(request: NudgeRequest) -> dict[str, Any]:
    sid = request.session_id or str(uuid.uuid4())
    profile, tx_path = _session_profile_and_tx(sid)
    monthly_variable = float(pd.read_csv(tx_path)["amount"].sum())
    g = calculate_goal_plan(profile, monthly_variable, sid)
    return evaluate_purchase(request.amount, request.description, g, profile, sid)


@app.post("/chat")
def cfo_chat(request: ChatRequest) -> dict[str, Any]:
    profile, _ = _session_profile_and_tx(request.session_id)
    return chat(request.message, request.session_id, profile)


@app.post("/analyze/statement")
def statement(req: StatementRequest) -> dict[str, Any]:
    sid = str(uuid.uuid4())
    return analyze_statement(req.model_dump(), sid)


@app.get("/portfolio/live")
def portfolio_live(session_id: str | None = None) -> dict[str, Any]:
    sid = session_id or str(uuid.uuid4())
    profile, tx_path = _session_profile_and_tx(sid)
    monthly_variable = float(pd.read_csv(tx_path)["amount"].sum())
    g = calculate_goal_plan(profile, monthly_variable, sid)
    return live_portfolio(profile, g, sid)


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)) -> dict[str, Any]:
    sid = str(uuid.uuid4())
    content = await file.read()
    return process_upload(file.filename, content, sid)


@app.post("/graph/query")
def graph_query(req: GraphRequest) -> dict[str, Any]:
    profile, _ = _session_profile_and_tx(req.session_id)
    return query_graph(req.query, profile, req.session_id)


@app.get("/news/sentiment")
def sentiment() -> dict[str, Any]:
    sid = str(uuid.uuid4())
    return analyze_news_sentiment(sid)


@app.get("/tax/optimize")
def tax_optimize(session_id: str | None = None) -> dict[str, Any]:
    sid = session_id or str(uuid.uuid4())
    profile, _ = _session_profile_and_tx(sid)
    return optimize_tax(profile, sid)


@app.post("/report/monthly")
def monthly_report(session_id: str | None = None) -> dict[str, Any]:
    sid = session_id or str(uuid.uuid4())
    profile, tx_path = _session_profile_and_tx(sid)
    return generate_monthly_report(profile, tx_path, sid)


@app.get("/retirement/plan")
def retirement(session_id: str | None = None) -> dict[str, Any]:
    sid = session_id or str(uuid.uuid4())
    profile, _ = _session_profile_and_tx(sid)
    return retirement_plan(profile, sid)


@app.get("/macro/climate")
def macro() -> dict[str, Any]:
    sid = str(uuid.uuid4())
    return macro_climate(sid)


@app.get("/audit/{session_id}")
def audit_session(session_id: str) -> dict[str, Any]:
    entries = memory_agent.load_session(session_id)
    return {"session_id": session_id, "events": entries}


@app.post("/memory/save")
def memory_save(payload: dict[str, Any]) -> dict[str, Any]:
    session_id = payload.get("session_id", str(uuid.uuid4()))
    agent = payload.get("agent", "manual")
    event_type = payload.get("event_type", "decision")
    summary = payload.get("summary", "manual save")
    data = payload.get("data", {})
    return memory_agent.save_entry(session_id, agent, event_type, summary, data)


@app.get("/memory/load")
def memory_load(agent: str | None = None, event_type: str | None = None, limit: int = 5) -> dict[str, Any]:
    return {"entries": memory_agent.load_recent(agent=agent, event_type=event_type, limit=limit)}


@app.post("/rag/query")
def rag_query(request: RAGQueryRequest, session_id: str | None = None) -> dict[str, Any]:
    """Query the RAG knowledge base for financial intelligence."""
    sid = session_id or str(uuid.uuid4())
    try:
        hits = rag_engine.query(request.question, k=max(1, int(request.top_k)))
        formatted_hits = []
        for hit in hits:
            formatted_hits.append({
                "text": hit.get("text", ""),
                "source": hit.get("metadata", {}).get("source_name") or "unknown",
                "similarity": round(max(0.0, 1.0 - float(hit.get("distance", 1.0))), 4),
            })
        memory_agent.save_entry(sid, "rag_engine", "query", f"Query: {request.question[:50]}", {"top_k": request.top_k, "results_count": len(formatted_hits)})
        return {
            "session_id": sid,
            "query": request.question,
            "results": formatted_hits,
            "count": len(formatted_hits),
        }
    except Exception as e:
        return {"session_id": sid, "error": str(e), "results": []}


@app.post("/rag/upsert")
def rag_upsert(request: RAGUpsertRequest, session_id: str | None = None) -> dict[str, Any]:
    """Add or update a document in the RAG knowledge base."""
    sid = session_id or str(uuid.uuid4())
    try:
        metadata = request.metadata or {"source_name": "manual_upload"}
        row_id = rag_engine.upsert_text(request.text, metadata)
        memory_agent.save_entry(sid, "rag_engine", "upsert", f"Added {len(request.text)} chars", {"row_id": row_id, "metadata": metadata})
        return {
            "session_id": sid,
            "row_id": row_id,
            "status": "success",
            "message": "Document added to knowledge base",
        }
    except Exception as e:
        return {"session_id": sid, "error": str(e), "status": "failed"}


@app.get("/rag/stats")
def rag_stats() -> dict[str, Any]:
    """Get RAG knowledge base statistics."""
    try:
        collection = rag_engine.collection
        count = collection.count()
        return {
            "status": "ok",
            "collection_name": "finpath_knowledge",
            "total_documents": count,
            "embedding_model": "all-MiniLM-L6-v2",
            "db_path": rag_engine.db_path,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
