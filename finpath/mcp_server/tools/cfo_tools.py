from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import format_audit_appendix, format_error, post_json


def register(app: FastMCP) -> None:
    @app.tool()
    async def chat_with_cfo(message: str, session_id: str = "mcp-session-001") -> str:
        """
        Chat with FinPath's dual-persona CFO advisor for decision-ready finance guidance.
        Used by: cfo_chat_agent.
        Returns: conversational recommendation, history length, and audit trail.
        """
        try:
            payload = await post_json("/chat", {"message": message, "session_id": session_id})
            lines = [
                "CFO Chat Response",
                "",
                f"- Session ID: {payload.get('session_id', session_id)}",
                f"- History Length: {payload.get('history_length', 'n/a')}",
                "",
                str(payload.get("response", "No response text.")),
            ]
            return "\n".join(lines) + format_audit_appendix(payload)
        except Exception as err:  # noqa: BLE001
            return format_error("chat_with_cfo", err)

    @app.tool()
    async def analyze_financial_statement(
        revenue: list[float],
        expenses: list[float],
        cashflow: list[float],
        company_name: str,
        period: str,
    ) -> str:
        """
        Run financial statement intelligence including DCF, variance, comps, and forecast.
        Used by: financial_statement_agent.
        Returns: valuation analysis and audit-backed explanation.
        """
        try:
            payload = await post_json(
                "/analyze/statement",
                {
                    "company_name": company_name,
                    "period": period,
                    "financial_data": {
                        "revenue": revenue,
                        "expenses": expenses,
                        "cashflow": cashflow,
                    },
                },
            )
            dcf = payload.get("dcf", {})
            lines = [
                "Financial Statement Analysis",
                "",
                f"- Company: {payload.get('company_name', company_name)}",
                f"- Period: {payload.get('period', period)}",
                f"- Enterprise Value (DCF): INR {dcf.get('enterprise_value', 'n/a')}",
                f"- Terminal Value: INR {dcf.get('terminal_value', 'n/a')}",
                "",
                "Comparable Analysis:",
                str(payload.get("comparable_analysis", "n/a")),
                "",
                "Cash Flow Forecast:",
                str(payload.get("cash_flow_forecast", "n/a")),
            ]
            return "\n".join(lines) + format_audit_appendix(payload)
        except Exception as err:  # noqa: BLE001
            return format_error("analyze_financial_statement", err)
