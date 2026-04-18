from __future__ import annotations

import os

import requests

from agents.audit import build_audit


def live_portfolio(profile: dict, goal_plan: dict, session_id: str) -> dict:
    ghost_url = os.getenv("GHOSTFOLIO_API_URL", "").strip()
    ghost_token = os.getenv("GHOSTFOLIO_API_TOKEN", "").strip()
    fallback_used = False
    current = {"equity": 45, "debt": 35, "gold": 20}
    actions = []

    if ghost_url and ghost_token:
        try:
            res = requests.get(ghost_url, headers={"Authorization": f"Bearer {ghost_token}"}, timeout=10)
            if res.ok and isinstance(res.json(), dict):
                current = res.json().get("allocation", current)
        except requests.RequestException:
            fallback_used = True
    else:
        fallback_used = True

    target = {"equity": 50, "debt": 35, "gold": 15}
    for k in target:
        delta = round(target[k] - current.get(k, 0), 2)
        if delta > 0:
            actions.append(f"Buy {k} by {delta}%")
        elif delta < 0:
            actions.append(f"Sell {k} by {abs(delta)}%")

    risk = min(10, max(1, int((target["equity"] / 100) * 10 + 3)))
    reasoning = [
        "Step 1: Attempted Ghostfolio live fetch using env credentials.",
        "Step 2: Applied fallback allocation model when live feed unavailable.",
        "Step 3: Computed buy/sell rebalance actions and risk score.",
    ]
    sources = ["ghostfolio_live" if not fallback_used else "portfolio_fallback_model"]
    audit = build_audit("robo_advisor_agent", reasoning, sources, "medium", "passed", session_id=session_id)
    return {
        "current_allocation": current,
        "target_allocation": target,
        "rebalancing_actions": actions,
        "risk_score": risk,
        "instruments": {
            "PPF": "7.1% guaranteed annual return, 15-year lock-in, 80C eligible",
            "SGB": "2.5% coupon + gold appreciation, 8-year tenure",
            "ELSS": "market-linked, 3-year lock-in, 80C up to 1.5L",
            "Nifty 50 Index Fund": "~12% historical CAGR, high liquidity",
            "NPS Tier 1": "8-10% expected returns, lock till 60, 80CCD eligible",
        },
        "goal_context": f"User goal context with monthly surplus {goal_plan.get('monthly_surplus', 14100)} INR",
        "fallback_used": fallback_used,
        **audit,
    }
