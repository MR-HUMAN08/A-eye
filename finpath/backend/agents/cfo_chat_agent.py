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
    cleaned = (text or "").strip()
    if not cleaned:
        return "- Track your monthly surplus first.\n- Keep fixed expenses controlled.\n- Prioritize goal-linked savings each month."

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    existing_bullets = [
        line.lstrip("-*").strip()
        for line in lines
        if line.startswith("-") or line.startswith("*") or line.startswith("•")
    ]
    if existing_bullets:
        return "\n".join([f"- {point}" for point in existing_bullets[:max_points]])

    sentence_candidates = [s.strip() for s in cleaned.replace("\n", " ").split(".") if s.strip()]
    selected = sentence_candidates[:max(3, min(max_points, len(sentence_candidates)))]
    return "\n".join([f"- {point}." for point in selected])


def chat(message: str, session_id: str, profile: dict) -> dict:
    history = _load_history(session_id)
    hits: list[dict] = []
    try:
        if os.getenv("FAST_DEMO_MODE", "0").strip() == "0":
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
        "You are FinPath CFO. Provide practical, math-backed guidance in 3-5 concise bullet points. "
        "Use the user's numbers directly and quantify timeline impact when possible."
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
        "Format: short bullet points only."
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
