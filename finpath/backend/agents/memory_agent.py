from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MEMORY_PATH = Path(__file__).resolve().parents[1] / "memory" / "agent_memory.json"


def _load_all() -> list[dict[str, Any]]:
    if not MEMORY_PATH.exists():
        return []
    return json.loads(MEMORY_PATH.read_text(encoding="utf-8"))


def _save_all(items: list[dict[str, Any]]) -> None:
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def load_recent(agent: str | None = None, event_type: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    items = _load_all()
    filtered = []
    for item in reversed(items):
        if agent and item.get("agent") != agent:
            continue
        if event_type and item.get("event_type") != event_type:
            continue
        filtered.append(item)
        if len(filtered) >= limit:
            break
    return list(reversed(filtered))


def save_entry(session_id: str, agent: str, event_type: str, summary: str, data: dict[str, Any]) -> dict[str, Any]:
    items = _load_all()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "agent": agent,
        "event_type": event_type,
        "summary": summary,
        "data": data,
    }
    items.append(entry)
    _save_all(items)
    return entry


def load_session(session_id: str) -> list[dict[str, Any]]:
    return [e for e in _load_all() if e.get("session_id") == session_id]
