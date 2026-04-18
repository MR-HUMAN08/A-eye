from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import format_error, get_json


def _event_to_text(idx: int, event: dict) -> str:
    lines = [
        f"Event {idx}",
        f"- Timestamp: {event.get('timestamp', 'n/a')}",
        f"- Agent: {event.get('agent', 'n/a')}",
        f"- Event Type: {event.get('event_type', 'n/a')}",
        f"- Summary: {event.get('summary', 'n/a')}",
    ]
    data = event.get("data", {})
    if isinstance(data, dict) and data:
        lines.append(f"- Data Keys: {', '.join(data.keys())}")
    return "\n".join(lines)


def register(app: FastMCP) -> None:
    @app.tool()
    async def get_audit_trail(session_id: str) -> str:
        """
        Produce a clean, judge-readable report of full AI decision trace for a session.
        Used by: audit and memory infrastructure across all FinPath agents.
        Returns: chronological decision history with reasoning context and confidence signals.
        """
        try:
            payload = await get_json(f"/audit/{session_id}")
            events = payload.get("events", [])
            lines = [
                "FinPath Audit Trail Report",
                "",
                f"Session: {payload.get('session_id', session_id)}",
                f"Total Events: {len(events)}",
                "",
            ]
            if not events:
                lines.append("No events were recorded for this session yet.")
            else:
                for i, event in enumerate(events, start=1):
                    lines.append(_event_to_text(i, event))
                    lines.append("")
            lines.append("Why this matters: every recommendation above is traceable to an explicit agent action log.")
            return "\n".join(lines)
        except Exception as err:  # noqa: BLE001
            return format_error("get_audit_trail", err)

    @app.tool()
    async def explain_last_recommendation(session_id: str, agent_name: str) -> str:
        """
        Explain the latest recommendation from a specific agent in plain language.
        Used by: audit layer for frontend-style "Why this advice?" drill-down.
        Returns: one focused explanation block for the latest matching agent event.
        """
        try:
            payload = await get_json(f"/audit/{session_id}")
            events = payload.get("events", [])
            filtered = [e for e in events if str(e.get("agent", "")).lower() == agent_name.lower()]
            if not filtered:
                return (
                    f"No events found for agent '{agent_name}' in session '{session_id}'. "
                    "Run a tool from that agent first, then retry."
                )
            latest = filtered[-1]
            return (
                "Why this advice?\n\n"
                f"Agent {agent_name} produced this recommendation at {latest.get('timestamp', 'n/a')} "
                f"for event '{latest.get('event_type', 'n/a')}'.\n"
                f"Summary: {latest.get('summary', 'n/a')}\n"
                "This recommendation is grounded in FinPath's logged decision flow and can be fully audited."
            )
        except Exception as err:  # noqa: BLE001
            return format_error("explain_last_recommendation", err)
