from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


def build_audit(
    agent: str,
    reasoning_chain: list[str],
    rag_sources: list[str],
    confidence: str,
    hallucination_guard: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    return {
        "audit": {
            "session_id": session_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "reasoning_chain": reasoning_chain,
            "rag_sources": rag_sources,
            "confidence": confidence,
            "hallucination_guard": hallucination_guard,
        }
    }
