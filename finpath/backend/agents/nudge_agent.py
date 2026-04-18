from __future__ import annotations

from agents import memory_agent
from agents.audit import build_audit
from agents.hallucination_guard import check
from agents.ollama_helper import run_ollama


def evaluate_purchase(amount: float, description: str, goal_plan: dict, profile: dict, session_id: str) -> dict:
    name = str(profile.get("name", "the user"))
    monthly_needed = float(goal_plan.get("monthly_savings_needed", 1))
    delay_days = max(1, int(round((amount / max(monthly_needed, 1)) * 30)))
    prompt = (
        f"Purchase amount: {amount}, description: {description}. "
        f"Goal monthly required savings: {monthly_needed}. Delay estimate: {delay_days} days. "
        f"Respond as an empathetic but direct real-time nudge for {name} in plain English."
    )
    text = run_ollama("You are Nudge Agent.", prompt)
    guard = check(text)
    reasoning = [
        "Step 1: Computed immediate delay estimate from purchase vs goal savings requirement.",
        "Step 2: Generated plain-English nudge with current user context.",
        "Step 3: Applied hallucination guard before return.",
    ]
    audit = build_audit("nudge_agent", reasoning, guard["sources"], "high", guard["status"], session_id=session_id)
    memory_agent.save_entry(
        session_id,
        "nudge_agent",
        "nudge_response",
        "Generated purchase nudge",
        {"amount": amount, "description": description, "delay_days": delay_days},
    )
    return {
        "delay_days": delay_days,
        "nudge": guard["text"],
        "decision": "reconsider" if amount >= 500 else "proceed_with_caution",
        **audit,
    }
