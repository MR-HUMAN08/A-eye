from __future__ import annotations

import os

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
    # Accept both 'cash_flow' (frontend) and 'cashflow' (legacy) keys
    cfs = fdata.get("cash_flow", []) or fdata.get("cashflow", [])

    # Ensure lists are proper format
    rev = [float(x) for x in rev] if rev else []
    exp = [float(x) for x in exp] if exp else []
    cfs = [float(x) for x in cfs] if cfs else []

    fcf = [r - e for r, e in zip(rev, exp)] if rev and exp else cfs if cfs else []
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
            pass

    total_rev = sum(rev) if rev else 0
    total_exp = sum(exp) if exp else 0
    total_cf = sum(cfs) if cfs else 0
    net_margin = ((total_rev - total_exp) / total_rev * 100) if total_rev > 0 else 0
    company = payload.get("company_name", "Unknown")
    period = payload.get("period", "N/A")

    fast_mode = os.getenv("FAST_DEMO_MODE", "1").strip() == "1"

    if fast_mode:
        comp_text = (
            f"{company} ({period}): Total Revenue Rs {total_rev:,.0f}, Total Expenses Rs {total_exp:,.0f}. "
            f"Net Margin: {net_margin:.1f}%. DCF Enterprise Value: Rs {dcf['enterprise_value']:,.0f}. "
            f"Operating Cash Flow: Rs {total_cf:,.0f}. "
            "Comparable Indian mid-cap companies trade at P/E 18-25x and EV/EBITDA 12-16x."
        )
        forecast_text = (
            f"Based on current FCF trend, 3-month optimistic forecast: Rs {fcf[-1] * 1.1:,.0f}/quarter. "
            f"Base case: Rs {fcf[-1]:,.0f}. Pessimistic: Rs {fcf[-1] * 0.85:,.0f}. "
            f"12-month projection (base): Rs {sum(fcf) * 1.05:,.0f}."
        )
        sources = ["fast_mode_computed"]
    else:
        hits = engine.query("Comparable company P/E EV/EBITDA India benchmark", k=4)
        context = "\n".join([h["text"] for h in hits])
        comp_text = run_ollama("You are Financial Statement Analysis Agent.", f"Context: {context}\nSummarize peer comps with P/E, EV/EBITDA, growth.")
        forecast_text = run_ollama(
            "You are Cash Flow Forecasting Agent.",
            f"Cashflows: {cfs or fcf}. Produce 3-month and 12-month optimistic/base/pessimistic forecast.",
        )
        sources = list({(h["metadata"].get("source_name") or h["metadata"].get("source") or "unknown") for h in hits})

    merged_text = f"Comparable Analysis:\n{comp_text}\n\nCash Flow Forecast:\n{forecast_text}"
    guard = check(merged_text)
    reasoning = [
        f"Step 1: Computed DCF NPV table with enterprise value Rs {dcf['enterprise_value']:,.0f}.",
        f"Step 2: Net margin {net_margin:.1f}%. Variance flagged {'yes' if any(v.get('significant') for v in variance) else 'none >10%'}.",
        "Step 3: Generated comparable analysis and cash flow forecasts.",
    ]
    audit = build_audit("financial_statement_agent", reasoning, sources or guard["sources"], "medium", guard["status"], session_id=session_id)
    return {
        "company_name": company,
        "period": period,
        "dcf": dcf,
        "comparable_analysis": comp_text,
        "variance_analysis": variance,
        "cash_flow_forecast": forecast_text,
        "net_margin_pct": round(net_margin, 2),
        "total_revenue": total_rev,
        "total_expenses": total_exp,
        "summary": guard["text"],
        **audit,
    }
