from __future__ import annotations

from agents.audit import build_audit


def macro_climate(session_id: str) -> dict:
    repo_rate = 6.5
    gsec = 7.1
    if repo_rate > 6:
        signal = "hawkish"
        adjustment = {"equity": -10, "debt": +10, "gold": 0}
    elif repo_rate < 5:
        signal = "dovish"
        adjustment = {"equity": +10, "debt": -10, "gold": 0}
    else:
        signal = "neutral"
        adjustment = {"equity": 0, "debt": 0, "gold": 0}

    audit = build_audit(
        "macro_agent",
        [
            "Step 1: Loaded repo rate and 10Y G-Sec yield from configured fallback values.",
            "Step 2: Classified macro stance as hawkish/neutral/dovish.",
            "Step 3: Derived portfolio allocation tilt from macro stance.",
        ],
        ["macro_fallback_feed"],
        "medium",
        "passed",
        session_id=session_id,
    )
    return {
        "repo_rate": repo_rate,
        "gsec_yield": gsec,
        "macro_signal": signal,
        "portfolio_adjustment": adjustment,
        "reasoning": "Higher rates support a larger debt allocation; lower rates support more equity.",
        **audit,
    }
