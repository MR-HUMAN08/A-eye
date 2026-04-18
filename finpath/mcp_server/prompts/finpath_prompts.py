from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register(app: FastMCP) -> None:
    @app.prompt(
        name="finpath-demo-flow",
        description=(
            "The complete FinPath demo flow. Shows a live user's spending analysis, goal status, "
            "nudge response to a purchase, and full audit trail. Use this for the live hackathon demo."
        ),
    )
    def finpath_demo_flow(purchase_amount: float, purchase_description: str) -> str:
        return (
            "Run the following MCP tools in order and present outputs as a single narrative:\n"
            "1) analyze_spending\n"
            "2) calculate_goal_plan\n"
            f"3) evaluate_purchase(amount={purchase_amount}, description='{purchase_description}')\n"
            "4) get_audit_trail(session_id='mcp-session-001')\n\n"
            "Conclude with: decision recommendation + explainability summary."
        )

    @app.prompt(
        name="finpath-cfo-brief",
        description=(
            "Full CFO monthly briefing. Covers spending health, live portfolio, tax optimisation, "
            "retirement outlook, and market sentiment. Returns a decision-ready executive summary."
        ),
    )
    def finpath_cfo_brief() -> str:
        return (
            "Run this monthly CFO brief pipeline:\n"
            "1) analyze_spending\n"
            "2) get_live_portfolio\n"
            "3) optimize_taxes\n"
            "4) get_retirement_projection\n"
            "5) get_market_sentiment\n\n"
            "Then return a 5-point executive summary with immediate actions."
        )

    @app.prompt(
        name="finpath-explain-decision",
        description=(
            "Explainable AI drill-down. Shows the full reasoning chain, RAG sources, and confidence levels "
            "for any agent's last recommendation. Directly demonstrates FinPath's auditable AI architecture."
        ),
    )
    def finpath_explain_decision(session_id: str, agent_name: str) -> str:
        return (
            "Run explain_last_recommendation with the provided inputs and format it as a user-facing panel:\n"
            f"- session_id: {session_id}\n"
            f"- agent_name: {agent_name}\n\n"
            "Title the panel as: Why this advice?"
        )

    @app.prompt(
        name="finpath-goal-health-check",
        description=(
            "Periodic goal health check. Assesses goal trajectory, shows highest-impact spending reduction, "
            "tax savings opportunity, and macro environment impact on investment plan."
        ),
    )
    def finpath_goal_health_check(months_elapsed: int) -> str:
        return (
            "Run this quarterly goal-health sequence:\n"
            f"1) check_goal_progress(months_elapsed={months_elapsed})\n"
            "2) simulate_monthly_impact(monthly_reduction=2000, category='food delivery')\n"
            "3) optimize_taxes\n"
            "4) get_macro_climate\n\n"
            "Summarize top risk, top opportunity, and next 30-day action plan."
        )
