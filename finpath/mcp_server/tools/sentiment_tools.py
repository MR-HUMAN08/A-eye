from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import format_audit_appendix, format_error, get_json


def register(app: FastMCP) -> None:
    @app.tool()
    async def get_market_sentiment() -> str:
        """
        Fetch cross-asset market sentiment and map impact to the user's financial goals.
        Used by: sentiment_agent.
        Returns: category-wise sentiment, impact mapping, and audit trail.
        """
        try:
            payload = await get_json("/news/sentiment")
            lines = ["Market Sentiment", ""]
            for row in payload.get("sentiment_by_category", []):
                lines.append(
                    f"- {row.get('category', 'unknown')}: {row.get('sentiment', 'neutral')} | Impact: {row.get('goal_impact', 'n/a')}"
                )
            if len(lines) == 2:
                lines.append(str(payload.get("summary", "No sentiment summary available.")))
            return "\n".join(lines) + format_audit_appendix(payload)
        except Exception as err:  # noqa: BLE001
            return format_error("get_market_sentiment", err)

    @app.tool()
    async def get_goal_market_impact() -> str:
        """
        Explain how current real-estate sentiment affects the user's goal trajectory.
        Used by: sentiment_agent.
        Returns: real-estate-specific market impact statement with audit details.
        """
        try:
            payload = await get_json("/news/sentiment")
            rows = payload.get("sentiment_by_category", [])
            real_estate = [r for r in rows if str(r.get("category", "")).lower() == "real estate"]
            lines = ["Goal Market Impact", ""]
            if real_estate:
                row = real_estate[0]
                lines.append(f"Real Estate Sentiment: {row.get('sentiment', 'neutral')}")
                lines.append(f"Impact on Hyderabad House Goal: {row.get('goal_impact', 'n/a')}")
            else:
                lines.append("Real Estate sentiment data is not currently available.")
            return "\n".join(lines) + format_audit_appendix(payload)
        except Exception as err:  # noqa: BLE001
            return format_error("get_goal_market_impact", err)
