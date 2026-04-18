from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import format_audit_appendix, format_error, get_json


def register(app: FastMCP) -> None:
    @app.tool()
    async def calculate_goal_plan() -> str:
        """
        Calculate house-goal feasibility with inflation-adjusted target and savings runway.
        Used by: goal_agent.
        Returns: target amount, daily/monthly savings need, feasibility verdict, and audit trail.
        """
        try:
            payload = await get_json("/goal")
            lines = [
                "Goal Plan",
                "",
                f"- Feasibility: {payload.get('goal_feasibility', 'unknown')}",
                f"- Inflation Adjusted Target: INR {payload.get('inflation_adjusted_target', 'n/a')}",
                f"- Monthly Savings Needed: INR {payload.get('monthly_savings_needed', 'n/a')}",
                f"- Daily Savings Needed: INR {payload.get('daily_savings_needed', 'n/a')}",
                f"- Monthly Surplus: INR {payload.get('monthly_surplus', 'n/a')}",
                "",
                str(payload.get("summary", "No summary available.")),
            ]
            return "\n".join(lines) + format_audit_appendix(payload)
        except Exception as err:  # noqa: BLE001
            return format_error("calculate_goal_plan", err)

    @app.tool()
    async def check_goal_progress(months_elapsed: int) -> str:
        """
        Evaluate whether the user is ahead or behind goal trajectory after N months.
        Used by: goal_agent.
        Returns: expected vs actual savings trajectory with ahead/behind verdict.
        """
        try:
            payload = await get_json("/goal")
            needed = float(payload.get("monthly_savings_needed", 0.0))
            surplus = float(payload.get("monthly_surplus", 0.0))
            required_total = round(months_elapsed * needed, 2)
            actual_total = round(months_elapsed * max(surplus, 0.0), 2)
            delta = round(actual_total - required_total, 2)
            status = "ahead" if delta >= 0 else "behind"
            lines = [
                "Goal Progress Check",
                "",
                f"- Months elapsed: {months_elapsed}",
                f"- Required cumulative savings: INR {required_total}",
                f"- Estimated cumulative savings at current surplus: INR {actual_total}",
                f"- Status: {status} by INR {abs(delta)}",
            ]
            return "\n".join(lines) + format_audit_appendix(payload)
        except Exception as err:  # noqa: BLE001
            return format_error("check_goal_progress", err)
