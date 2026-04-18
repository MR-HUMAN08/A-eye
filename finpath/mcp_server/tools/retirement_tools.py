from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import format_audit_appendix, format_error, get_json


def register(app: FastMCP) -> None:
    @app.tool()
    async def get_retirement_projection() -> str:
        """
        Retrieve long-horizon retirement and legacy wealth projections for the user.
        Used by: retirement_agent.
        Returns: corpus checkpoints across ages and generational wealth estimate.
        """
        try:
            payload = await get_json("/retirement/plan")
            checkpoints = payload.get("checkpoints", [])
            lines = ["Retirement Projection", "", "Corpus Checkpoints:"]
            for cp in checkpoints:
                lines.append(f"- Age {cp.get('age', '?')}: INR {cp.get('corpus', 'n/a')}")
            lines.append(f"Legacy Estimate: INR {payload.get('legacy_estimate', 'n/a')}")
            return "\n".join(lines) + format_audit_appendix(payload)
        except Exception as err:  # noqa: BLE001
            return format_error("get_retirement_projection", err)

    @app.tool()
    async def simulate_nps_contribution(monthly_contribution: float) -> str:
        """
        Simulate retirement corpus uplift from an updated monthly NPS contribution.
        Used by: retirement_agent with MCP-side projection scaling.
        Returns: updated corpus estimate and improvement vs current projection.
        """
        try:
            payload = await get_json("/retirement/plan")
            current = float(payload.get("nps_projection_at_60", 0.0))
            baseline = float(payload.get("nps_monthly_contribution", 1.0))
            ratio = monthly_contribution / baseline if baseline else 1.0
            updated = round(current * ratio, 2)
            delta = round(updated - current, 2)
            lines = [
                "NPS Contribution Simulation",
                "",
                f"- Current monthly contribution: INR {baseline}",
                f"- Simulated monthly contribution: INR {monthly_contribution}",
                f"- Current NPS corpus at 60: INR {current}",
                f"- Updated NPS corpus at 60: INR {updated}",
                f"- Improvement: INR {delta}",
            ]
            return "\n".join(lines) + format_audit_appendix(payload)
        except Exception as err:  # noqa: BLE001
            return format_error("simulate_nps_contribution", err)
