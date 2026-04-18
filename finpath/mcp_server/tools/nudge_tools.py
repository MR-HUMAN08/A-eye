from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import format_audit_appendix, format_error, post_json


def register(app: FastMCP) -> None:
    @app.tool()
    async def evaluate_purchase(amount: float, description: str) -> str:
        """
        Star demo tool: evaluate a purchase in real time and show how it affects the user's life goal.
        Used by: nudge_agent.
        Returns: delay in days, recommendation to proceed/reconsider, and full audit trail.
        """
        try:
            payload = await post_json("/nudge", {"amount": amount, "description": description})
            lines = [
                "Purchase Nudge",
                "",
                f"- Purchase: {description}",
                f"- Amount: INR {amount}",
                f"- Goal Delay: {payload.get('delay_days', 'n/a')} day(s)",
                f"- Decision: {payload.get('decision', 'n/a')}",
                "",
                str(payload.get("nudge", "No nudge text available.")),
            ]
            return "\n".join(lines) + format_audit_appendix(payload)
        except Exception as err:  # noqa: BLE001
            return format_error("evaluate_purchase", err)

    @app.tool()
    async def simulate_monthly_impact(monthly_reduction: float, category: str) -> str:
        """
        Simulate monthly spend reduction impact and estimate goal acceleration in months.
        Used by: nudge_agent.
        Returns: acceleration estimate and behavior recommendation with audit details.
        """
        try:
            payload = await post_json(
                "/nudge",
                {
                    "amount": monthly_reduction,
                    "description": f"Monthly reduction simulation for {category}",
                },
            )
            delay_days = float(payload.get("delay_days", 0.0))
            acceleration_months = round(delay_days / 30.0, 2)
            lines = [
                "Monthly Impact Simulation",
                "",
                f"- Category: {category}",
                f"- Monthly Reduction: INR {monthly_reduction}",
                f"- Estimated Goal Acceleration: {acceleration_months} month(s)",
                f"- Recommendation: {payload.get('decision', 'n/a')}",
            ]
            return "\n".join(lines) + format_audit_appendix(payload)
        except Exception as err:  # noqa: BLE001
            return format_error("simulate_monthly_impact", err)
