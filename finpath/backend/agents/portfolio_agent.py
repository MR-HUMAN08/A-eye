from __future__ import annotations

import os

from agents import memory_agent
from agents.audit import build_audit
from agents.hallucination_guard import check
from agents.ollama_helper import run_ollama


def recommend_portfolio(profile: dict, goal_plan: dict, session_id: str) -> dict:
    name = str(profile.get("name", "the user"))
    risk = profile.get("risk_appetite", "moderate").lower()
    if risk == "low":
        base = {"conservative": {"equity": 20, "debt": 60, "gold": 20}, "balanced": {"equity": 40, "debt": 45, "gold": 15}, "aggressive": {"equity": 60, "debt": 25, "gold": 15}}
    elif risk == "high":
        base = {"conservative": {"equity": 35, "debt": 50, "gold": 15}, "balanced": {"equity": 55, "debt": 30, "gold": 15}, "aggressive": {"equity": 75, "debt": 15, "gold": 10}}
    else:
        base = {"conservative": {"equity": 30, "debt": 55, "gold": 15}, "balanced": {"equity": 50, "debt": 35, "gold": 15}, "aggressive": {"equity": 70, "debt": 20, "gold": 10}}

    fast_mode = os.getenv("FAST_DEMO_MODE", "1").strip() == "1"
    if fast_mode:
        text = (
            f"Based on your {risk} risk preference, start with the balanced allocation and review monthly. "
            "Use Nifty 50 index funds for equity, PPF/debt funds for debt, and SGB for gold exposure."
        )
    else:
        prompt = (
            f"{name} goal status: {goal_plan.get('goal_feasibility')}, monthly surplus: {goal_plan.get('monthly_surplus')}. "
            "Explain the 3 allocation options with Indian instruments: Nifty 50, PPF, SGB, ELSS, NPS."
        )
        text = run_ollama("You are Portfolio Agent.", prompt)
    guard = check(text)
    reasoning = [
        "Step 1: Built risk-based conservative/balanced/aggressive allocations.",
        "Step 2: Mapped each sleeve to India-specific instruments.",
        "Step 3: Generated explainable recommendation and applied guard.",
    ]
    audit = build_audit("portfolio_agent", reasoning, guard["sources"], "medium", guard["status"], session_id=session_id)
    memory_agent.save_entry(session_id, "portfolio_agent", "decision", "Updated portfolio recommendation", {"risk": risk})
    return {"allocations": base, "summary": guard["text"], **audit}
