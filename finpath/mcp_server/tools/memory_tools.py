from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import format_error, get_json, post_json


def register(app: FastMCP) -> None:
    @app.tool()
    async def save_agent_memory(session_id: str, agent: str, event_type: str, summary: str) -> str:
        """
        Persist an explicit agent memory record for future reasoning continuity.
        Used by: memory_agent.
        Returns: confirmation record with timestamp and session metadata.
        """
        try:
            payload = await post_json(
                "/memory/save",
                {
                    "session_id": session_id,
                    "agent": agent,
                    "event_type": event_type,
                    "summary": summary,
                    "data": {},
                },
            )
            return (
                "Memory Persisted\n\n"
                f"- Session: {payload.get('session_id', session_id)}\n"
                f"- Agent: {payload.get('agent', agent)}\n"
                f"- Event Type: {payload.get('event_type', event_type)}\n"
                f"- Timestamp: {payload.get('timestamp', 'n/a')}"
            )
        except Exception as err:  # noqa: BLE001
            return format_error("save_agent_memory", err)

    @app.tool()
    async def load_agent_memory(agent: str | None = None, event_type: str | None = None) -> str:
        """
        Load recent memory entries as a chronological timeline for agent context reuse.
        Used by: memory_agent.
        Returns: recent memory entries filtered by agent and/or event type.
        """
        try:
            params = {}
            if agent:
                params["agent"] = agent
            if event_type:
                params["event_type"] = event_type
            payload = await get_json("/memory/load", params=params)
            entries = payload.get("entries", [])
            lines = ["Agent Memory Timeline", ""]
            if not entries:
                lines.append("No memory entries found for the selected filter.")
            for idx, entry in enumerate(entries, start=1):
                lines.append(
                    f"{idx}. {entry.get('timestamp', 'n/a')} | {entry.get('agent', 'n/a')} | "
                    f"{entry.get('event_type', 'n/a')} | {entry.get('summary', 'n/a')}"
                )
            return "\n".join(lines)
        except Exception as err:  # noqa: BLE001
            return format_error("load_agent_memory", err)