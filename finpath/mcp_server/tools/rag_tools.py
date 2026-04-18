from __future__ import annotations

import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import format_error


BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from rag.rag_engine import engine  # noqa: E402


def _format_hits(hits: list[dict], title: str) -> str:
    lines = [title, ""]
    if not hits:
        lines.append("No matching knowledge chunks found.")
        return "\n".join(lines)
    for i, hit in enumerate(hits, start=1):
        metadata = hit.get("metadata", {})
        source = metadata.get("source_name") or metadata.get("source") or "unknown"
        distance = hit.get("distance", 1.0)
        similarity = round(max(0.0, 1.0 - float(distance)), 4)
        snippet = str(hit.get("text", "")).strip().replace("\n", " ")
        if len(snippet) > 280:
            snippet = snippet[:280] + "..."
        lines.extend(
            [
                f"{i}. Source: {source}",
                f"   Similarity: {similarity}",
                f"   Snippet: {snippet}",
            ]
        )
    return "\n".join(lines)


def register(app: FastMCP) -> None:
    @app.tool()
    async def query_financial_knowledge(question: str, top_k: int = 5) -> str:
        """
        Query FinPath's ChromaDB knowledge base directly for grounded financial intelligence.
        Used by: rag_engine (direct vector retrieval).
        Returns: top-k chunks with sources, similarity scores, and snippets.
        """
        try:
            hits = engine.query(question, k=max(1, int(top_k)))
            return _format_hits(hits, "Direct RAG Query Results")
        except Exception as err:  # noqa: BLE001
            return format_error("query_financial_knowledge", err)

    @app.tool()
    async def get_india_finance_benchmarks(category: str) -> str:
        """
        Retrieve India-specific financial benchmark references for a requested category.
        Used by: rag_engine (benchmark retrieval).
        Returns: benchmark chunks and source citations from finpath_knowledge.
        """
        try:
            query = f"{category} benchmark India 60000 income"
            hits = engine.query(query, k=5)
            return _format_hits(hits, f"India Finance Benchmarks: {category}")
        except Exception as err:  # noqa: BLE001
            return format_error("get_india_finance_benchmarks", err)
