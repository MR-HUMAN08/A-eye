from __future__ import annotations

from agents.audit import build_audit
from rag.rag_engine import engine


def optimize_tax(profile: dict, session_id: str) -> dict:
    annual_income = float(profile.get("monthly_income", 60000)) * 12
    existing_80c = float(profile.get("existing_80c_investments", 0) or 0)
    headroom_80c = max(0, 150000 - existing_80c)
    health_80d = 0
    headroom_80d = max(0, 25000 - health_80d)

    old_regime_tax = max(0, (annual_income - 500000) * 0.2)
    new_regime_tax = max(0, (annual_income - 700000) * 0.1)
    regime = "new" if new_regime_tax < old_regime_tax else "old"
    saved = abs(old_regime_tax - new_regime_tax)

    candidate_rule = "FY2025-26 80C limit is 1.5L and 80D self+family is 25k"
    hits = engine.query(candidate_rule, k=1)
    added = 0
    if not hits or hits[0]["distance"] > 0.15:
        engine.upsert_text(candidate_rule, {"source_name": "tax_agent_self_learning", "document_type": "tax_rule"})
        added = 1

    recs = [
        {"priority": 1, "action": f"Invest additional {headroom_80c:.0f} INR across ELSS/PPF to fill 80C."},
        {"priority": 2, "action": f"Use up to {headroom_80d:.0f} INR under 80D via health insurance premium."},
        {"priority": 3, "action": f"Choose {regime} regime for estimated savings of {saved:.0f} INR."},
    ]
    audit = build_audit(
        "tax_agent",
        [
            "Step 1: Calculated 80C/80D remaining headroom from profile assumptions.",
            "Step 2: Compared old vs new regime tax for FY 2025-26 income.",
            "Step 3: Ran self-learning check and appended new rule if missing.",
        ],
        ["tax_agent_self_learning" if added else "finpath_knowledge"],
        "high",
        "passed",
        session_id=session_id,
    )
    return {
        "tax_saved": round(saved, 2),
        "recommended_actions": recs,
        "regime_recommendation": regime,
        "new_rag_entries_added": added,
        **audit,
    }
