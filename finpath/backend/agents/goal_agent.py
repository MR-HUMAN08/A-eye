from __future__ import annotations

import os

from agents import memory_agent
from agents.audit import build_audit
from agents.hallucination_guard import check
from agents.ollama_helper import run_ollama


def calculate_goal_plan(profile: dict, monthly_variable_spend: float, session_id: str) -> dict:
    name = str(profile.get("name", "User"))
    income = float(profile.get("monthly_income", 0) or 0)
    fixed = float(profile.get("monthly_fixed_expenses", 0) or 0)
    years = float(profile.get("goal_timeline_years", 0) or 0)
    goal_amount = float(profile.get("goal_amount", 0) or 0)
    inflation = float(profile.get("inflation_rate", 0.06))

    if years <= 0:
        years = 1.0
    if goal_amount < 0:
        goal_amount = 0.0

    future_target = goal_amount * ((1 + inflation) ** years)
    months = int(years * 12)
    monthly_needed = future_target / months
    daily_needed = monthly_needed / 30
    monthly_surplus = income - fixed - monthly_variable_spend
    feasibility = "feasible" if monthly_surplus >= monthly_needed else "at_risk"

    fast_mode = os.getenv("FAST_DEMO_MODE", "1").strip() == "1"
    if fast_mode:
        text = (
            f"Your monthly surplus is Rs {monthly_surplus:.2f} and required monthly savings is Rs {monthly_needed:.2f}. "
            "Increase surplus or extend goal timeline to improve feasibility."
        )
    else:
        prompt = (
            f"Target future value: {future_target:.2f}, monthly needed: {monthly_needed:.2f}, "
            f"daily needed: {daily_needed:.2f}, monthly surplus: {monthly_surplus:.2f}. "
            f"Explain in plain English for {name} and include action steps."
        )
        try:
            text = run_ollama("You are Goal Modeling Agent.", prompt)
        except Exception:
            text = (
                f"Your monthly surplus is Rs {monthly_surplus:.2f} and required monthly savings is Rs {monthly_needed:.2f}. "
                "Increase surplus or extend goal timeline to improve feasibility."
            )
    guard = check(text)
    reasoning = [
        "Step 1: Computed inflation-adjusted target using profile inflation and timeline.",
        "Step 2: Calculated monthly and daily savings requirements.",
        "Step 3: Compared required savings to current surplus and generated guidance.",
    ]
    audit = build_audit("goal_agent", reasoning, guard["sources"], "high", guard["status"], session_id=session_id)
    memory_agent.save_entry(session_id, "goal_agent", "goal_update", "Updated goal feasibility", {"feasibility": feasibility})
    return {
        "goal_feasibility": feasibility,
        "inflation_adjusted_target": round(future_target, 2),
        "monthly_savings_needed": round(monthly_needed, 2),
        "daily_savings_needed": round(daily_needed, 2),
        "monthly_surplus": round(monthly_surplus, 2),
        "summary": guard["text"],
        **audit,
    }
