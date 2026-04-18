from __future__ import annotations

import math

from agents import memory_agent
from agents.audit import build_audit
from agents.hallucination_guard import check
from agents.ollama_helper import run_ollama


def evaluate_purchase(amount: float, description: str, goal_plan: dict, profile: dict, session_id: str) -> dict:
    name = str(profile.get("name", "the user"))
    income = float(profile.get("monthly_income", 0) or 0)
    goal_amount = float(profile.get("goal_amount", 0) or 0)
    existing_savings = float(profile.get("existing_savings", 0) or 0)
    goal = str(profile.get("goal", "financial goal"))
    goal_years = float(profile.get("goal_timeline_years", 5) or 5)
    expected_returns = float(profile.get("expected_returns", 0.12) or 0.12)
    monthly_surplus = float(goal_plan.get("monthly_surplus", 0) or 0)

    # ── Core delay calculation ──────────────────────────────────────
    #
    # Intuitive formula:
    #   daily_savings = monthly_surplus / 30
    #   delay_days    = purchase_amount / daily_savings
    #
    # This tells the user: "This purchase eats up N days of your savings."
    #
    # Compound-growth adjustment (opportunity cost):
    #   If the user invests their surplus at `expected_returns` annual rate,
    #   Rs X today grows to X * (1 + r)^(years_remaining) by goal date.
    #   So the *true* cost of spending Rs X now is larger than Rs X.
    #   We compute: effective_cost = amount * (1 + monthly_rate) ^ months_remaining
    #   Then: delay_days = effective_cost / daily_savings
    #
    # Guard: if monthly_surplus <= 0 the goal is already infeasible,
    #        so we show delay based on a nominal Rs 100/day savings rate
    #        to still give a meaningful number.

    if monthly_surplus > 0:
        daily_savings = monthly_surplus / 30.0

        # Opportunity-cost adjustment
        remaining_goal = max(0, goal_amount - existing_savings)
        months_remaining = max(1, remaining_goal / monthly_surplus)
        monthly_rate = expected_returns / 12.0
        compounding_factor = (1 + monthly_rate) ** min(months_remaining, goal_years * 12)
        effective_cost = amount * compounding_factor

        delay_days = int(math.ceil(effective_cost / daily_savings))
    else:
        # Surplus is zero or negative — goal is infeasible, but still show impact
        nominal_daily = max(1, income / 30.0) if income > 0 else 100
        delay_days = int(math.ceil(amount / nominal_daily))

    # Ensure at least 1 day for any purchase
    delay_days = max(1, delay_days)

    # ── Decision logic ──────────────────────────────────────────────
    # Percentage of monthly income thresholds:
    #   > 5%  → reconsider
    #   > 2%  → proceed with caution
    #   else  → proceed
    if income > 0:
        pct = amount / income
        if pct >= 0.05:
            decision = "reconsider"
        elif pct >= 0.02:
            decision = "proceed_with_caution"
        else:
            decision = "proceed"
    else:
        decision = "reconsider" if amount >= 500 else "proceed"

    system = (
        "You are the Nudge Agent for FinPath, an Indian personal finance app. "
        "Always use INR (₹ or Rs) for currency. Never use $ or USD. "
        "Respond as an empathetic but direct real-time nudge in 2-3 sentences."
    )
    prompt = (
        f"User: {name}, monthly income: Rs {income:.0f}, goal: {goal}.\n"
        f"Purchase: Rs {amount:.0f} on {description}.\n"
        f"Monthly surplus: Rs {monthly_surplus:.0f}, daily savings capacity: Rs {monthly_surplus / 30:.0f}.\n"
        f"This purchase delays the goal by approximately {delay_days} day(s).\n"
        f"Goal remaining: Rs {max(0, goal_amount - existing_savings):.0f} over {goal_years:.1f} years.\n"
        f"Decision recommendation: {decision}.\n"
        f"Give a concise, empathetic nudge in plain English with the delay impact."
    )
    text = run_ollama(system, prompt)
    guard = check(text)
    reasoning = [
        f"Step 1: Daily savings capacity = Rs {monthly_surplus:.0f} / 30 = Rs {monthly_surplus / 30:.0f}.",
        f"Step 2: Opportunity-cost adjusted purchase impact = {delay_days} day(s) of savings.",
        f"Step 3: Income-ratio threshold check → decision: {decision}.",
        "Step 4: Generated plain-English nudge and applied hallucination guard.",
    ]
    audit = build_audit("nudge_agent", reasoning, guard["sources"], "high", guard["status"], session_id=session_id)
    memory_agent.save_entry(
        session_id,
        "nudge_agent",
        "nudge_response",
        "Generated purchase nudge",
        {"amount": amount, "description": description, "delay_days": delay_days, "decision": decision},
    )
    return {
        "delay_days": delay_days,
        "nudge": guard["text"],
        "decision": decision,
        **audit,
    }

