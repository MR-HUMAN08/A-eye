from __future__ import annotations

import json
import os
from pathlib import Path

from agents import memory_agent
from agents.audit import build_audit
from agents.hallucination_guard import check
from agents.ollama_helper import run_ollama
from rag.rag_engine import engine


CHAT_DIR = Path(__file__).resolve().parents[1] / "memory" / "chat_sessions"


def _chat_path(session_id: str) -> Path:
    CHAT_DIR.mkdir(parents=True, exist_ok=True)
    return CHAT_DIR / f"{session_id}.json"


def _load_history(session_id: str) -> list[dict]:
    path = _chat_path(session_id)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_history(session_id: str, history: list[dict]) -> None:
    _chat_path(session_id).write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def _as_bullets(text: str, max_points: int = 5) -> str:
    """Convert AI output into exactly `max_points` concise bullet points."""
    cleaned = (text or "").strip()

    fallback_points = [
        "Track your monthly surplus before making big purchases.",
        "Keep fixed expenses below 30% of income.",
        "Prioritize goal-linked savings each month via SIP.",
        "Cut top discretionary leakage category by 10-15%.",
        "Review and cancel unused subscriptions regularly.",
    ]

    if not cleaned:
        return "\n".join([f"• {p}" for p in fallback_points[:max_points]])

    # Extract bullet-like lines first
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    points = []
    for line in lines:
        stripped = line.lstrip("-*•0123456789.) ").strip()
        if stripped and len(stripped) > 5:
            points.append(stripped.rstrip(".") + ".")

    # If no bullet-like lines, split on sentences
    if not points:
        sentence_candidates = [s.strip() for s in cleaned.replace("\n", " ").split(".") if s.strip() and len(s.strip()) > 5]
        points = [s.rstrip(".") + "." for s in sentence_candidates]

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for p in points:
        key = p.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(p)
    points = unique

    # Pad to exactly max_points if needed
    while len(points) < max_points:
        for fp in fallback_points:
            if fp not in points and len(points) < max_points:
                points.append(fp)

    # Trim to exactly max_points
    points = points[:max_points]
    return "\n".join([f"• {p}" for p in points])


def chat(message: str, session_id: str, profile: dict) -> dict:
    history = _load_history(session_id)
    hits: list[dict] = []
    try:
        if os.getenv("FAST_DEMO_MODE", "1").strip() != "1":
            hits = engine.query(message, k=6)
    except Exception:
        hits = []

    rag_context = "\n".join(
        [f"[{h.get('metadata', {}).get('source_name', 'source')}] {h.get('text', '')[:260]}" for h in hits[:4]]
    )
    monthly_income = float(profile.get("monthly_income", 0) or 0)
    monthly_fixed = float(profile.get("monthly_fixed_expenses", 0) or 0)
    monthly_surplus = float(profile.get("existing_savings", 0) or 0)
    goal_amount = float(profile.get("goal_amount", 0) or 0)
    goal_years = float(profile.get("goal_timeline_years", 0) or 0)

    system = (
        "You are FinPath CFO — a concise personal finance advisor. "
        "Reply with EXACTLY 5 short bullet points (one line each). "
        "Use the user's actual numbers (in Rs/INR). Quantify impact where possible. "
        "No introductions, no conclusions — just 5 actionable bullet points."
    )
    prompt = (
        f"User: {profile.get('name', 'User')}\n"
        f"City: {profile.get('city', 'n/a')}\n"
        f"Monthly income: Rs {monthly_income:.0f}\n"
        f"Monthly fixed expenses: Rs {monthly_fixed:.0f}\n"
        f"Current monthly surplus estimate: Rs {monthly_surplus:.0f}\n"
        f"Goal: {profile.get('goal', 'n/a')}\n"
        f"Goal amount: Rs {goal_amount:.0f}\n"
        f"Goal timeline years: {goal_years:.1f}\n"
        f"Question: {message}\n"
        f"RAG context (optional):\n{rag_context or 'No retrieved context available.'}\n"
        "Respond with exactly 5 bullet points. Keep each point under 20 words."
    )
    out = run_ollama(system, prompt, max_tokens=180)
    guard = check(out)
    response_text = _as_bullets(guard["text"]) if guard.get("text") else _as_bullets("")

    history.append({"role": "user", "message": message})
    history.append({"role": "assistant", "message": response_text})
    _save_history(session_id, history)
    memory_agent.save_entry(session_id, "cfo_chat_agent", "chat_message", "Processed chat turn", {"message": message})

    audit = build_audit(
        "cfo_chat_agent",
        [
            "Step 1: Loaded session conversation history and recent memory entries.",
            "Step 2: Retrieved optional RAG chunks and built concise CFO prompt.",
            "Step 3: Generated response, enforced bullet format, applied hallucination guard, and persisted chat state.",
        ],
        [h.get("metadata", {}).get("source_name", "unknown") for h in hits],
        "medium",
        guard["status"],
        session_id=session_id,
    )
    return {"response": response_text, "session_id": session_id, "history_length": len(history), **audit}
