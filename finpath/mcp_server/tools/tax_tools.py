from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import format_audit_appendix, format_error, get_json


def _estimate_tax(annual_income: float, regime: str) -> float:
    income = max(0.0, annual_income)
    regime = regime.lower().strip()
    if regime == "old":
        slabs = [(250000, 0.0), (250000, 0.05), (500000, 0.2), (float("inf"), 0.3)]
    else:
        slabs = [(300000, 0.0), (300000, 0.05), (300000, 0.1), (300000, 0.15), (300000, 0.2), (float("inf"), 0.3)]
    tax = 0.0
    remaining = income
    for limit, rate in slabs:
        if remaining <= 0:
            break
        taxable = min(remaining, limit)
        tax += taxable * rate
        remaining -= taxable
    return round(tax * 1.04, 2)


def register(app: FastMCP) -> None:
    @app.tool()
    async def optimize_taxes() -> str:
        """
        Optimize Indian tax posture with 80C/80D headroom and regime recommendation.
        Used by: tax_agent.
        Returns: top tax actions, estimated savings, and audit trace.
        """
        try:
            payload = await get_json("/tax/optimize")
            actions = payload.get("recommended_actions", [])
            lines = [
                "Tax Optimization",
                "",
                f"- Estimated Tax Saved: INR {payload.get('tax_saved', 'n/a')}",
                f"- Recommended Regime: {payload.get('regime_recommendation', 'n/a')}",
                f"- New RAG Rules Added: {payload.get('new_rag_entries_added', 'n/a')}",
                "",
                "Recommended Actions:",
            ]
            for action in actions:
                lines.append(f"- P{action.get('priority', '?')}: {action.get('action', 'n/a')}")
            return "\n".join(lines) + format_audit_appendix(payload)
        except Exception as err:  # noqa: BLE001
            return format_error("optimize_taxes", err)

    @app.tool()
    async def calculate_tax_liability(annual_income: float, regime: str = "new") -> str:
        """
        Estimate annual tax liability in plain English for old/new regimes.
        Used by: tax_agent data and MCP-side slab estimator.
        Returns: simplified tax estimate and recommendation context.
        """
        try:
            payload = await get_json("/tax/optimize")
            liability = _estimate_tax(annual_income, regime)
            lines = [
                "Tax Liability Estimate",
                "",
                f"- Annual Income: INR {annual_income}",
                f"- Regime: {regime}",
                f"- Estimated Liability (incl. 4% cess): INR {liability}",
                f"- Backend Regime Recommendation: {payload.get('regime_recommendation', 'n/a')}",
            ]
            return "\n".join(lines) + format_audit_appendix(payload)
        except Exception as err:  # noqa: BLE001
            return format_error("calculate_tax_liability", err)
