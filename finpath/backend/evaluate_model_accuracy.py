from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

LABELS = ["emi", "food", "shopping", "travel", "investment"]
LABEL_SET = set(LABELS)


def load_dataset(dataset_path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with dataset_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"transaction_narration", "label"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError(f"Dataset missing required columns {required}. Found: {reader.fieldnames}")
        for row in reader:
            text = (row.get("transaction_narration") or "").strip()
            label = (row.get("label") or "").strip().lower()
            if not text or label not in LABEL_SET:
                continue
            rows.append({"transaction_narration": text, "label": label})
    if not rows:
        raise ValueError("No valid rows found in dataset.")
    return rows


def build_batch_prompt(items: list[dict[str, str]]) -> str:
    lines = []
    for i, row in enumerate(items, start=1):
        lines.append(f"{i}. {row['transaction_narration']}")
    examples = "\n".join(lines)
    return (
        "Classify each transaction narration into exactly one label from: "
        "emi, food, shopping, travel, investment.\n"
        "Rules:\n"
        "- Return ONLY valid JSON.\n"
        "- Output must be a JSON array with exactly one object per input item.\n"
        "- Each object format: {\"id\": <number>, \"label\": \"<one_of_labels>\"}.\n"
        "- Keep original order and ids.\n\n"
        f"Transactions:\n{examples}"
    )


def extract_json_array(text: str) -> list[dict[str, Any]] | None:
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[.*\]", text, flags=re.DOTALL)
    if match:
        candidate = match.group(0)
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            return None
    return None


def recover_labels_fallback(text: str, expected: int) -> list[str]:
    tokens = re.findall(r"\b(emi|food|shopping|travel|investment)\b", text.lower())
    labels = tokens[:expected]
    if len(labels) < expected:
        labels.extend(["invalid"] * (expected - len(labels)))
    return labels


def call_groq(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    base = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    timeout = int(os.getenv("GROQ_TIMEOUT", "60"))

    max_retries = int(os.getenv("GROQ_MAX_RETRIES", "6"))
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0,
                    "max_tokens": max_tokens,
                },
                timeout=(10, timeout),
            )
            if response.status_code in {429, 500, 502, 503, 504}:
                wait = min(20.0, 1.5 * (2 ** attempt))
                time.sleep(wait)
                continue
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            return str(payload["choices"][0]["message"]["content"])
        except Exception as err:  # noqa: BLE001
            last_error = err
            wait = min(20.0, 1.5 * (2 ** attempt))
            time.sleep(wait)

    raise RuntimeError(f"Groq call failed after retries: {last_error}")


def call_ollama(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    timeout = int(os.getenv("OLLAMA_TIMEOUT", "60"))
    prompt = f"System:\n{system_prompt}\n\nUser:\n{user_prompt}\n\nAssistant:"

    response = requests.post(
        f"{base}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0, "num_predict": max_tokens},
        },
        timeout=(10, timeout),
    )
    response.raise_for_status()
    return str(response.json().get("response", ""))


def classify_batch(provider: str, items: list[dict[str, str]], max_tokens: int) -> list[str]:
    system = (
        "You are a strict financial transaction classifier for Indian personal finance. "
        "Output ONLY valid JSON and no explanation."
    )
    user = build_batch_prompt(items)

    if provider == "groq":
        raw = call_groq(system, user, max_tokens)
    elif provider == "ollama":
        raw = call_ollama(system, user, max_tokens)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    parsed = extract_json_array(raw)
    if not parsed:
        return recover_labels_fallback(raw, len(items))

    predicted: list[str] = []
    by_id: dict[int, str] = {}
    for obj in parsed:
        if not isinstance(obj, dict):
            continue
        idx = obj.get("id")
        label = str(obj.get("label", "")).strip().lower()
        if isinstance(idx, int) and label:
            by_id[idx] = label

    for i in range(1, len(items) + 1):
        label = by_id.get(i, "invalid")
        if label not in LABEL_SET:
            label = "invalid"
        predicted.append(label)

    return predicted


def compute_metrics(y_true: list[str], y_pred: list[str]) -> dict[str, Any]:
    assert len(y_true) == len(y_pred)
    total = len(y_true)
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = (correct / total) * 100 if total else 0.0

    matrix: dict[str, dict[str, int]] = {
        t: {p: 0 for p in LABELS + ["invalid"]} for t in LABELS
    }
    for t, p in zip(y_true, y_pred):
        matrix[t][p if p in matrix[t] else "invalid"] += 1

    per_class: dict[str, dict[str, float]] = {}
    for label in LABELS:
        tp = matrix[label][label]
        fp = sum(matrix[other][label] for other in LABELS if other != label)
        fn = sum(matrix[label][other] for other in LABELS if other != label) + matrix[label]["invalid"]
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        per_class[label] = {
            "precision": round(precision * 100, 2),
            "recall": round(recall * 100, 2),
            "f1": round(f1 * 100, 2),
            "support": int(sum(matrix[label][k] for k in matrix[label])),
        }

    macro_f1 = sum(v["f1"] for v in per_class.values()) / len(per_class)
    invalid_count = sum(1 for p in y_pred if p == "invalid")

    return {
        "accuracy_percent": round(accuracy, 2),
        "total_samples": total,
        "correct": correct,
        "incorrect": total - correct,
        "invalid_predictions": invalid_count,
        "label_distribution": dict(Counter(y_true)),
        "prediction_distribution": dict(Counter(y_pred)),
        "per_class": per_class,
        "macro_f1_percent": round(macro_f1, 2),
        "confusion_matrix": matrix,
    }


def run_evaluation(
    provider: str,
    dataset_path: Path,
    batch_size: int,
    max_tokens: int,
    sleep_seconds: float,
) -> dict[str, Any]:
    rows = load_dataset(dataset_path)
    y_true: list[str] = []
    y_pred: list[str] = []

    total_batches = (len(rows) + batch_size - 1) // batch_size
    start = time.time()

    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(rows))
        batch = rows[start_idx:end_idx]
        try:
            predictions = classify_batch(provider, batch, max_tokens=max_tokens)
        except Exception as err:  # noqa: BLE001
            print(f"[{provider}] batch {batch_idx + 1}/{total_batches} failed: {err}", flush=True)
            predictions = ["invalid"] * len(batch)

        y_true.extend([row["label"] for row in batch])
        y_pred.extend(predictions)

        print(
            f"[{provider}] batch {batch_idx + 1}/{total_batches} processed "
            f"({end_idx}/{len(rows)} samples)",
            flush=True,
        )
        if sleep_seconds > 0 and batch_idx < total_batches - 1:
            time.sleep(sleep_seconds)

    metrics = compute_metrics(y_true, y_pred)
    elapsed = round(time.time() - start, 2)

    result = {
        "provider": provider,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(dataset_path),
        "batch_size": batch_size,
        "max_tokens": max_tokens,
        "elapsed_seconds": elapsed,
        "metrics": metrics,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Model accuracy validation for FinPath transaction classification")
    parser.add_argument("--provider", choices=["groq", "ollama"], required=True)
    parser.add_argument("--dataset", default="/home/harini/cbit/archive/finance_test_1000.csv")
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--sleep-seconds", type=float, default=0.05)
    parser.add_argument("--output-dir", default="/home/harini/cbit/finpath/backend/reports")
    args = parser.parse_args()

    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path)

    result = run_evaluation(
        provider=args.provider,
        dataset_path=Path(args.dataset),
        batch_size=max(1, args.batch_size),
        max_tokens=max(128, args.max_tokens),
        sleep_seconds=max(0.0, args.sleep_seconds),
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"accuracy_{args.provider}_{stamp}.json"
    out_file.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("\n=== Accuracy Summary ===")
    print(f"Provider: {result['provider']}")
    print(f"Accuracy: {result['metrics']['accuracy_percent']}%")
    print(f"Macro F1: {result['metrics']['macro_f1_percent']}%")
    print(f"Samples: {result['metrics']['total_samples']}")
    print(f"Invalid predictions: {result['metrics']['invalid_predictions']}")
    print(f"Report: {out_file}")


if __name__ == "__main__":
    main()
