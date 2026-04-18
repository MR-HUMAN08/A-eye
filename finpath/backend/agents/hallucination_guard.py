from __future__ import annotations

from typing import Any

from rag.rag_engine import engine


def check(output_text: str, threshold: float = 0.75) -> dict[str, Any]:
    hits = engine.query(output_text[:800], k=4)
    supported = [h for h in hits if h["distance"] <= threshold]
    if supported:
        sources = []
        for hit in supported:
            src = hit["metadata"].get("source_name") or hit["metadata"].get("source") or "unknown_source"
            if src not in sources:
                sources.append(src)
        return {"status": "passed", "text": output_text, "sources": sources}
    note = "\n\nNote: I'm less certain about this — no supporting document was found in the knowledge base."
    return {"status": "flagged", "text": output_text + note, "sources": []}
