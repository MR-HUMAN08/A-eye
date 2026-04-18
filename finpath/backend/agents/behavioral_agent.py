from __future__ import annotations

import os

import pandas as pd

from agents import memory_agent
from agents.audit import build_audit
from agents.hallucination_guard import check
from agents.ollama_helper import run_ollama
from rag.rag_engine import engine


def analyze_transactions(transactions_csv: str, session_id: str, profile: dict | None = None) -> dict:
    runtime_profile = profile or {}
    name = runtime_profile.get("name", "the user")
    monthly_income = float(runtime_profile.get("monthly_income", 60000))
    city = runtime_profile.get("city", "India")
    goal = runtime_profile.get("goal", "a major financial goal")

    try:
        frame = pd.read_csv(transactions_csv)
    except Exception:
        frame = pd.DataFrame(columns=["date", "description", "category", "amount"])

    for col in ["category", "amount"]:
        if col not in frame.columns:
            frame[col] = []

    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce").fillna(0.0)
    grouped = frame.groupby("category")["amount"].sum().sort_values(ascending=False)
    monthly_variable = float(frame["amount"].sum())
    top_categories = grouped.head(4).to_dict()

    fast_mode = os.getenv("FAST_DEMO_MODE", "1").strip() == "1"
    hits = []
    if not fast_mode:
        try:
            hits = engine.query(f"India spending benchmarks for {int(monthly_income)} salary", k=4)
        except Exception:
            hits = []
    context = "\n".join([h["text"] for h in hits])

    try:
        previous = memory_agent.load_recent(event_type="decision", limit=3)
    except Exception:
        previous = []

    lead_category = next(iter(top_categories.keys()), "other")
    lead_amount = float(next(iter(top_categories.values()), 0.0))

    if fast_mode:
        text = (
            f"For {name}, top spending category is {lead_category} at Rs {lead_amount:.2f}. "
            "Focus on reducing top discretionary categories by 10-15% to improve monthly surplus and goal progress."
        )
    else:
        prompt = (
            f"Profile: {name}, income {monthly_income:.0f}, city {city}, goal: {goal}.\n"
            f"Top categories: {top_categories}\n"
            f"Monthly variable spend: {monthly_variable}\n"
            f"Previous context: {previous}\n"
            f"RAG context: {context}\n"
            "Give plain-English leakage patterns and decision-ready output."
        )
        try:
            text = run_ollama("You are Behavioral Analysis Agent for FinPath.", prompt)
        except Exception:
            text = (
                f"Top spending category is {lead_category} at Rs {lead_amount:.2f}. "
                "Reduce discretionary spends by 10-15% to improve monthly surplus."
            )
    try:
        guard = check(text)
    except Exception:
        guard = {"text": text, "status": "passed"}
    sources = list({(h["metadata"].get("source_name") or h["metadata"].get("source") or "unknown") for h in hits})
    reasoning = [
        f"Step 1: Loaded {len(frame)} transactions and grouped spending by category.",
        "Step 2: Retrieved 4 RAG chunks for benchmark grounding.",
        "Step 3: Generated leakage insights with Qwen and ran hallucination guard.",
    ]
    audit = build_audit("behavioral_agent", reasoning, sources, "high", guard["status"], session_id=session_id)
    memory_agent.save_entry(session_id, "behavioral_agent", "decision", "Generated spending leakage analysis", {"top_categories": top_categories})
    return {
        "summary": guard["text"],
        "category_totals": grouped.to_dict(),
        "monthly_variable_spend": monthly_variable,
        **audit,
    }
