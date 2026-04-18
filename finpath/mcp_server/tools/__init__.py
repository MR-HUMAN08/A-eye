from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx


BACKEND_URL = os.getenv("FINPATH_BACKEND_URL", "http://localhost:8000")
TIMEOUT_SECONDS = 90.0
BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"


def format_audit_appendix(payload: dict[str, Any]) -> str:
    audit = payload.get("audit", {})
    if not audit:
        return "\n\n--- Audit Trail ---\nNo audit metadata was returned by the backend."
    agent = audit.get("agent", "unknown")
    confidence = audit.get("confidence", "unknown")
    sources = audit.get("rag_sources", [])
    guard = audit.get("hallucination_guard", "unknown")
    source_text = ", ".join(str(s) for s in sources) if isinstance(sources, list) and sources else "none"
    return (
        "\n\n--- Audit Trail ---\n"
        f"Agent: {agent} | Confidence: {confidence} | "
        f"Sources: {source_text} | Hallucination Guard: {guard}"
    )


def format_error(tool_name: str, err: Exception) -> str:
    return (
        f"{tool_name} could not complete right now. "
        f"Reason: {type(err).__name__}: {err}. "
        "Please retry in a few seconds."
    )


async def get_json(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        resp = await client.get(f"{BACKEND_URL}{path}", params=params)
        resp.raise_for_status()
        return resp.json()


async def post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        resp = await client.post(f"{BACKEND_URL}{path}", json=payload)
        resp.raise_for_status()
        return resp.json()


async def post_multipart(path: str, files: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        resp = await client.post(f"{BACKEND_URL}{path}", files=files)
        resp.raise_for_status()
        return resp.json()
