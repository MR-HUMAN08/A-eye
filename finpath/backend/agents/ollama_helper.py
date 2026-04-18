from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _build_prompt(system_prompt: str, user_prompt: str) -> str:
    return f"System:\n{system_prompt}\n\nUser:\n{user_prompt}\n\nAssistant:"


def _run_groq(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    base = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    timeout = int(os.getenv("GROQ_TIMEOUT", "12"))
    resp = requests.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": float(os.getenv("MODEL_TEMPERATURE", "0.2")),
            "max_tokens": int(max_tokens),
        },
        timeout=(10, timeout),
    )
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("Groq returned no choices")
    message = choices[0].get("message", {})
    text = str(message.get("content", "")).strip()
    if not text:
        raise RuntimeError("Groq returned empty content")
    return text


def _run_ollama(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    timeout = int(os.getenv("OLLAMA_TIMEOUT", "12"))
    prompt = _build_prompt(system_prompt, user_prompt)
    response = requests.post(
        f"{base}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False, "options": {"num_predict": max_tokens}},
        timeout=(10, timeout),
    )
    response.raise_for_status()
    return response.json().get("response", "").strip()


def run_ollama(system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
    """Primary LLM router: Groq first, Ollama fallback.

    Existing agents call this function name, so the signature is preserved.
    """
    primary = os.getenv("PRIMARY_MODEL_PROVIDER", "groq").lower().strip()
    if primary not in {"groq", "ollama"}:
        primary = "groq"

    first = _run_groq if primary == "groq" else _run_ollama
    second = _run_ollama if primary == "groq" else _run_groq

    try:
        return first(system_prompt, user_prompt, max_tokens)
    except Exception:
        try:
            return second(system_prompt, user_prompt, max_tokens)
        except Exception as err:
            return "" # Return empty string to allow caller to apply fallback logic
