from __future__ import annotations

from agents.audit import build_audit
from agents.hallucination_guard import check
from agents.ollama_helper import run_ollama
from rag.rag_engine import engine


def _dcf(fcf: list[float], discount_rate: float = 0.10, terminal_growth: float = 0.03) -> dict:
    npv_rows = []
    npv = 0.0
    for i, cash in enumerate(fcf, start=1):
        pv = cash / ((1 + discount_rate) ** i)
        npv_rows.append({"year": i, "fcf": cash, "pv": round(pv, 2)})
        npv += pv
    terminal = (fcf[-1] * (1 + terminal_growth)) / max(discount_rate - terminal_growth, 0.01)
    terminal_pv = terminal / ((1 + discount_rate) ** len(fcf))
    return {"npv_table": npv_rows, "terminal_value": round(terminal, 2), "enterprise_value": round(npv + terminal_pv, 2)}


def analyze_statement(payload: dict, session_id: str) -> dict:
    fdata = payload.get("financial_data", {})
    rev = fdata.get("revenue", [])
    exp = fdata.get("expenses", [])
    cfs = fdata.get("cashflow", [])
    
    # Ensure lists are proper format
    rev = list(rev) if rev else []
    exp = list(exp) if exp else []
    cfs = list(cfs) if cfs else []
    
    fcf = [float(r) - float(e) for r, e in zip(rev, exp)] if rev and exp else [float(x) for x in cfs] if cfs else []
    if not fcf:
        fcf = [100000, 120000, 140000]

    dcf = _dcf(fcf)
    planned = payload.get("planned", rev)
    if not planned:
        planned = rev
    
    variance = []
    for a, p in zip(rev, planned):
        try:
            a, p = float(a), float(p)
            if p and p != 0:
                v = ((a - p) / p) * 100
                variance.append({"actual": a, "planned": p, "variance_pct": round(v, 2), "significant": abs(v) > 10})
        except (ValueError, TypeError):
            pass  # Skip invalid entries

    hits = engine.query("Comparable company P/E EV/EBITDA India benchmark", k=4)
    context = "\n".join([h["text"] for h in hits])
    comp_text = run_ollama("You are Financial Statement Analysis Agent.", f"Context: {context}\nSummarize peer comps with P/E, EV/EBITDA, growth.")
    forecast_text = run_ollama(
        "You are Cash Flow Forecasting Agent.",
        f"Cashflows: {cfs or fcf}. Produce 3-month and 12-month optimistic/base/pessimistic forecast.",
    )

    merged_text = f"Comparable Analysis:\n{comp_text}\n\nCash Flow Forecast:\n{forecast_text}"
    guard = check(merged_text)
    sources = list({(h["metadata"].get("source_name") or h["metadata"].get("source") or "unknown") for h in hits})
    reasoning = [
        "Step 1: Computed DCF NPV table and terminal value.",
        "Step 2: Calculated variance vs planned and flagged >10% changes.",
        "Step 3: Retrieved peer benchmarks and generated comparable + forecast outputs.",
    ]
    audit = build_audit("financial_statement_agent", reasoning, sources or guard["sources"], "medium", guard["status"], session_id=session_id)
    return {
        "company_name": payload.get("company_name", "Unknown"),
        "period": payload.get("period", "N/A"),
        "dcf": dcf,
        "comparable_analysis": comp_text,
        "variance_analysis": variance,
        "cash_flow_forecast": forecast_text,
        "summary": guard["text"],
        **audit,
    }
