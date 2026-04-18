from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import format_audit_appendix, format_error, get_json


def register(app: FastMCP) -> None:
    @app.tool()
    async def get_portfolio_recommendation() -> str:
        """
        Provide 3-tier Indian portfolio allocation aligned to the user's risk and goal horizon.
        Used by: portfolio_agent.
        Returns: conservative/balanced/aggressive allocations and advisory summary.
        """
        try:
            payload = await get_json("/portfolio")
            allocations = payload.get("allocations", {})
            lines = ["Portfolio Recommendation", ""]
            for tier, mix in allocations.items():
                lines.append(f"{tier.title()}:")
                for k, v in mix.items():
                    lines.append(f"- {k}: {v}%")
                lines.append("")
            lines.append(str(payload.get("summary", "No summary available.")))
            return "\n".join(lines) + format_audit_appendix(payload)
        except Exception as err:  # noqa: BLE001
            return format_error("get_portfolio_recommendation", err)

    @app.tool()
    async def get_live_portfolio() -> str:
        """
        Retrieve live robo-advisor posture with rebalance actions and risk score.
        Used by: robo_advisor_agent.
        Returns: current/target allocation delta, rebalance actions, risk score, and audit.
        """
        try:
            payload = await get_json("/portfolio/live")
            lines = [
                "Live Portfolio",
                "",
                f"- Data Source: {payload.get('source', 'unknown')}",
                f"- Risk Score (1-10): {payload.get('risk_score', 'n/a')}",
                "- Rebalance Actions:",
            ]
            actions = payload.get("actions", [])
            if not actions:
                lines.append("  None needed.")
            else:
                for action in actions:
                    lines.append(f"  - {action}")
            lines.append("")
            lines.append(str(payload.get("summary", "No summary available.")))
            return "\n".join(lines) + format_audit_appendix(payload)
        except Exception as err:  # noqa: BLE001
            return format_error("get_live_portfolio", err)

    @app.tool()
    async def get_macro_climate() -> str:
        """
        Interpret RBI/macroeconomic climate and convert it into a portfolio tilt recommendation.
        Used by: macro_agent.
        Returns: repo-rate signal, climate label, suggested allocation tilt, and audit.
        """
        try:
            payload = await get_json("/macro/climate")
            lines = [
                "Macro Climate",
                "",
                f"- Repo Rate: {payload.get('repo_rate', 'n/a')}%",
                f"- 10Y G-Sec: {payload.get('gsec_10y', 'n/a')}%",
                f"- Climate: {payload.get('climate', 'unknown')}",
                f"- Recommendation: {payload.get('recommendation', 'n/a')}",
            ]
            return "\n".join(lines) + format_audit_appendix(payload)
        except Exception as err:  # noqa: BLE001
            return format_error("get_macro_climate", err)
