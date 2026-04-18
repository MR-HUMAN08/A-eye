#!/usr/bin/env python3
"""Merge cleaned datasets and repository docs into one RAG-ready corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = BASE_DIR / "data" / "processed"


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge cleaned corpora into one RAG input set")
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    processed_dir = args.processed_dir
    dataset_records = read_jsonl(processed_dir / "rag_corpus.jsonl")
    repo_records = read_jsonl(processed_dir / "repo_corpus.jsonl")

    merged: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()

    for record in dataset_records:
        text = record.get("text") or record.get("raw_text") or record.get("input") or ""
        canonical = stable_hash(f"dataset|{record.get('source_name', '')}|{text.strip().lower()}")
        if canonical in seen_hashes:
            continue
        seen_hashes.add(canonical)
        merged.append(
            {
                "source_kind": "dataset",
                "source_name": record.get("source_name"),
                "document_type": record.get("task_type"),
                "content": text,
                "metadata": record.get("metadata", {}),
                "row_hash": canonical,
            }
        )

    for record in repo_records:
        content = record.get("content", "")
        canonical = stable_hash(f"repo|{record.get('repo_name', '')}|{record.get('relative_path', '')}|{content.lower()}")
        if canonical in seen_hashes:
            continue
        seen_hashes.add(canonical)
        merged.append(
            {
                "source_kind": "repo",
                "source_name": record.get("repo_name"),
                "document_type": record.get("document_type"),
                "content": content,
                "metadata": {"relative_path": record.get("relative_path")},
                "row_hash": canonical,
            }
        )

    write_jsonl(processed_dir / "rag_input_corpus.jsonl", merged)
    (processed_dir / "rag_input_summary.json").write_text(
        json.dumps(
            {
                "dataset_records": len(dataset_records),
                "repo_records": len(repo_records),
                "merged_records": len(merged),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()