#!/usr/bin/env python3
"""Build a deduplicated document corpus from cloned financial-services repos.

This indexes markdown, JSON, YAML, and text files from the cloned Anthropic
plugin marketplace so the RAG layer can answer questions using the upstream
financial workflows and skills.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = BASE_DIR / "external_sources"
DEFAULT_OUTPUT_DIR = BASE_DIR / "data" / "processed"

ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".yml", ".yaml"}
ALLOWED_NAMES = {"README.md", "CLAUDE.md", "SKILL.md", "plugin.json", "marketplace.json", "mcp-categories.json"}


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def should_include(path: Path) -> bool:
    if path.name in ALLOWED_NAMES:
        return True
    return path.suffix.lower() in ALLOWED_EXTENSIONS


def classify_document(path: Path) -> str:
    if path.name == "SKILL.md":
        return "skill"
    if path.name.startswith("README"):
        return "readme"
    if path.name.endswith(".json"):
        return "json"
    if path.name.endswith((".yml", ".yaml")):
        return "yaml"
    return "text"


def build_records(source_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()

    for repo_dir in sorted(path for path in source_root.iterdir() if path.is_dir()):
        for file_path in repo_dir.rglob("*"):
            if not file_path.is_file() or not should_include(file_path):
                continue

            content = file_path.read_text(encoding="utf-8", errors="ignore").strip()
            if not content:
                continue

            record_hash = stable_hash(f"{repo_dir.name}|{file_path.relative_to(repo_dir)}|{content}")
            if record_hash in seen_hashes:
                continue
            seen_hashes.add(record_hash)

            records.append(
                {
                    "repo_name": repo_dir.name,
                    "relative_path": str(file_path.relative_to(repo_dir)),
                    "document_type": classify_document(file_path),
                    "content": content,
                    "row_hash": record_hash,
                }
            )

    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build repository document corpus")
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    records = build_records(args.source_root)
    write_jsonl(output_dir / "repo_corpus.jsonl", records)
    (output_dir / "repo_corpus_summary.json").write_text(
        json.dumps({"record_count": len(records), "source_root": str(args.source_root)}, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()