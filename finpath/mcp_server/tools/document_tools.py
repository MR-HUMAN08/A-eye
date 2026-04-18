from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import format_audit_appendix, format_error, post_multipart


def register(app: FastMCP) -> None:
    @app.tool()
    async def upload_and_analyze_document(file_path: str) -> str:
        """
        Upload a local financial document for extraction, analysis, and RAG indexing.
        Used by: document_intelligence_agent.
        Returns: extraction summary, goal relevance insights, new chunk count, and audit.
        """
        try:
            path = Path(file_path).expanduser().resolve()
            if not path.exists() or not path.is_file():
                return f"upload_and_analyze_document could not find file: {path}"
            with path.open("rb") as f:
                payload = await post_multipart("/documents/upload", {"file": (path.name, f, "application/octet-stream")})
            lines = [
                "Document Intelligence",
                "",
                f"- Filename: {payload.get('filename', path.name)}",
                f"- Summary: {payload.get('summary', payload.get('error', 'No summary'))}",
                f"- Goal Relevance: {payload.get('goal_relevance', 'n/a')}",
                f"- New Chunks Indexed: {payload.get('chunks_indexed', 'n/a')}",
            ]
            return "\n".join(lines) + format_audit_appendix(payload)
        except Exception as err:  # noqa: BLE001
            return format_error("upload_and_analyze_document", err)
