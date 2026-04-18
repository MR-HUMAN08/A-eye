from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import format_audit_appendix, format_error, get_json


def register(app: FastMCP) -> None:
    @app.tool()
    async def analyze_spending() -> str:
        """
        Analyze the user's transaction behavior to identify spending leakage patterns.
        Used by: behavioral_agent.
        Returns: category-wise spend, leakage insights, and audit trail.
        """
        try:
            payload = await get_json("/analyze")
            categories = payload.get("category_totals", {})
            summary = payload.get("summary", "No summary available.")
            lines = ["Spending Analysis", "", "Category Totals:"]
            for key, value in categories.items():
                lines.append(f"- {key}: INR {value}")
            lines.append("")
            lines.append("Leakage Insights:")
            lines.append(summary)
            return "\n".join(lines) + format_audit_appendix(payload)
        except Exception as err:  # noqa: BLE001
            return format_error("analyze_spending", err)

    @app.tool()
    async def get_leakage_report() -> str:
        """
        Generate a ranked leakage report with annualized savings opportunity.
        Used by: behavioral_agent.
        Returns: top three leakage categories and annual savings estimates.
        """
        try:
            payload = await get_json("/analyze")
            categories = payload.get("category_totals", {})
            ranked = sorted(categories.items(), key=lambda kv: kv[1], reverse=True)[:3]
            lines = ["Top 3 Spending Leakages", ""]
            for i, (name, monthly) in enumerate(ranked, start=1):
                annual = round(float(monthly) * 12 * 0.3, 2)
                lines.append(f"{i}. {name}: INR {monthly}/month | Est. annual savings if reduced 30%: INR {annual}")
            if not ranked:
                lines.append("No leakage categories available.")
            return "\n".join(lines) + format_audit_appendix(payload)
        except Exception as err:  # noqa: BLE001
            return format_error("get_leakage_report", err)
