from __future__ import annotations

from agents.audit import build_audit


def _future_value(monthly: float, annual_rate: float, years: int) -> float:
    r = annual_rate / 12
    n = years * 12
    return monthly * (((1 + r) ** n - 1) / r)


def retirement_plan(profile: dict, session_id: str) -> dict:
    current_age = int(profile.get("age", 28))
    years = 60 - current_age
    nps = _future_value(3000, 0.09, years)
    epf = _future_value(3600, 0.0815, years)
    post_house_monthly = float(profile.get("monthly_income", 60000)) * 0.2
    legacy = _future_value(post_house_monthly, 0.12, max(0, years - 5))

    checkpoints = {}
    for age in [30, 40, 50, 60]:
        y = max(0, age - current_age)
        checkpoints[str(age)] = {
            "nps": round(_future_value(3000, 0.09, y), 2),
            "epf": round(_future_value(3600, 0.0815, y), 2),
            "legacy": round(_future_value(post_house_monthly, 0.12, max(0, y - 5)), 2),
        }

    audit = build_audit(
        "retirement_agent",
        [
            "Step 1: Computed NPS corpus projection till age 60 at 9% CAGR.",
            "Step 2: Computed EPF projection at 8.15% interest.",
            "Step 3: Simulated post-house legacy corpus using Nifty-style CAGR assumption.",
        ],
        ["retirement_projection_model"],
        "medium",
        "passed",
        session_id=session_id,
    )
    return {
        "nps_corpus_at_60": round(nps, 2),
        "nps_lumpsum_60_pct": round(nps * 0.6, 2),
        "nps_annuity_40_pct": round(nps * 0.4, 2),
        "epf_corpus_at_60": round(epf, 2),
        "generational_wealth_projection": round(legacy, 2),
        "timeline": checkpoints,
        **audit,
    }
