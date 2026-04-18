#!/usr/bin/env python3
"""Download, clean, deduplicate, and normalize financial datasets.

Outputs:
- processed/merged_records.jsonl
- processed/instruction_corpus.jsonl
- processed/rag_corpus.jsonl
- processed/summary.json
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import requests

try:
    from datasets import load_dataset
except ImportError:  # pragma: no cover - optional dependency during file creation
    load_dataset = None


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = BASE_DIR / "dataset_manifest.json"
DEFAULT_OUTPUT_DIR = BASE_DIR / "data" / "processed"

NULL_TOKENS = {"", "na", "n/a", "null", "none", "nan", "�"}
CSV_ENCODINGS = ("utf-8", "utf-8-sig", "cp1252", "latin1")


@dataclass
class NormalizedRecord:
    source_name: str
    task_type: str
    input_text: str
    target_text: str | None
    raw_text: str
    row_hash: str
    metadata: dict[str, Any]


def load_manifest(manifest_path: Path) -> list[dict[str, Any]]:
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    return manifest["datasets"]


def normalize_column_name(column_name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", column_name.strip().lower())
    return cleaned.strip("_")


def normalize_value(value: Any) -> str | None:
    if pd.isna(value):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lower() in NULL_TOKENS:
            return None
        return re.sub(r"\s+", " ", stripped)
    return str(value)


def clean_dataframe(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [normalize_column_name(column) for column in frame.columns]
    frame = frame.replace(list(NULL_TOKENS), pd.NA)
    frame = frame.dropna(how="all")
    frame = frame.drop_duplicates()
    return frame.reset_index(drop=True)


def dataframe_row_to_text(row: pd.Series) -> str:
    parts: list[str] = []
    for column, value in row.items():
        normalized = normalize_value(value)
        if normalized is not None:
            parts.append(f"{column}: {normalized}")
    return " | ".join(parts)


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_input_target(frame: pd.DataFrame) -> tuple[str, str | None]:
    column_names = set(frame.columns)
    if {"transaction_narration", "label"}.issubset(column_names):
        return "transaction_narration", "label"
    if {"instruction", "output"}.issubset(column_names):
        return "instruction", "output"
    if {"instruction", "response"}.issubset(column_names):
        return "instruction", "response"
    if {"question", "answer"}.issubset(column_names):
        return "question", "answer"
    if {"prompt", "completion"}.issubset(column_names):
        return "prompt", "completion"
    if {"input", "output"}.issubset(column_names):
        return "input", "output"
    if {"text", "label"}.issubset(column_names):
        return "text", "label"
    return "", None


def dataframe_to_records(source_name: str, task_type: str, frame: pd.DataFrame) -> list[NormalizedRecord]:
    frame = clean_dataframe(frame)
    input_column, target_column = build_input_target(frame)
    records: list[NormalizedRecord] = []

    if input_column:
        for _, row in frame.iterrows():
            input_value = normalize_value(row.get(input_column))
            target_value = normalize_value(row.get(target_column)) if target_column else None
            if not input_value:
                continue
            raw_text = input_value if target_value is None else f"{input_value} -> {target_value}"
            canonical = f"{source_name}|{task_type}|{raw_text.lower()}"
            records.append(
                NormalizedRecord(
                    source_name=source_name,
                    task_type=task_type,
                    input_text=input_value,
                    target_text=target_value,
                    raw_text=raw_text,
                    row_hash=stable_hash(canonical),
                    metadata={"columns": list(frame.columns)},
                )
            )
        return records

    for _, row in frame.iterrows():
        text = dataframe_row_to_text(row)
        if not text:
            continue
        canonical = f"{source_name}|{task_type}|{text.lower()}"
        records.append(
            NormalizedRecord(
                source_name=source_name,
                task_type=task_type,
                input_text=text,
                target_text=None,
                raw_text=text,
                row_hash=stable_hash(canonical),
                metadata={"columns": list(frame.columns)},
            )
        )
    return records


def fetch_csv(url: str, limit: int = 0) -> pd.DataFrame:
    nrows = limit if limit > 0 else None
    for encoding in CSV_ENCODINGS:
        try:
            return pd.read_csv(url, encoding=encoding, nrows=nrows)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(url, encoding="latin1", nrows=nrows)


def fetch_zip_csv(url: str, limit: int = 0, source_name: str = "zip_dataset") -> list[tuple[str, pd.DataFrame]]:
    nrows = limit if limit > 0 else None
    for encoding in CSV_ENCODINGS:
        try:
            frame = pd.read_csv(url, compression="zip", encoding=encoding, nrows=nrows)
            return [(source_name, frame)]
        except UnicodeDecodeError:
            continue
    frame = pd.read_csv(url, compression="zip", encoding="latin1", nrows=nrows)
    return [(source_name, frame)]


def _streaming_dataset_to_frame(dataset: Any, limit: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    row_count = 0
    for row in dataset:
        rows.append(dict(row))
        row_count += 1
        if limit > 0 and row_count >= limit:
            break
    return pd.DataFrame(rows)


def fetch_huggingface(dataset_id: str, split: str | None, limit: int = 0) -> list[pd.DataFrame]:
    if load_dataset is None:
        raise RuntimeError("datasets package is not installed")

    # Streaming mode keeps memory bounded for very large datasets.
    if split and limit > 0:
        dataset = load_dataset(dataset_id, split=split, streaming=True)
        return [_streaming_dataset_to_frame(dataset, limit=limit)]

    if split and limit == 0:
        dataset = load_dataset(dataset_id, split=split)
        return [pd.DataFrame(dataset)]

    if not split and limit > 0:
        dataset_dict = load_dataset(dataset_id, streaming=True)
        frames: list[pd.DataFrame] = []
        for split_name in dataset_dict.keys():
            frames.append(_streaming_dataset_to_frame(dataset_dict[split_name], limit=limit))
        return frames

    if split:
        dataset = load_dataset(dataset_id, split=split)
        return [pd.DataFrame(dataset)]

    dataset = load_dataset(dataset_id)
    if isinstance(dataset, dict):
        return [pd.DataFrame(dataset[key]) for key in dataset.keys()]
    return [pd.DataFrame(dataset)]


def collect_frames(entry: dict[str, Any], limit: int = 0) -> list[tuple[str, pd.DataFrame]]:
    source_type = entry["source_type"]
    task_type = entry["task_type"]
    name = entry["name"]

    if source_type == "local_csv":
        for encoding in CSV_ENCODINGS:
            try:
                return [(name, pd.read_csv(entry["path"], encoding=encoding))]
            except UnicodeDecodeError:
                continue
        return [(name, pd.read_csv(entry["path"], encoding="latin1"))]
    if source_type == "csv_url":
        return [(name, fetch_csv(entry["url"], limit=limit))]
    if source_type == "zip_csv_url":
        return fetch_zip_csv(entry["url"], limit=limit, source_name=name)
    if source_type == "huggingface":
        return [
            (f"{name}_{index}", frame)
            for index, frame in enumerate(fetch_huggingface(entry["dataset_id"], entry.get("split"), limit=limit))
        ]
    if source_type == "kaggle":
        raise RuntimeError("manual_download_required:kaggle_credentials_or_local_files")
    raise ValueError(f"Unsupported source type: {source_type}")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build cleaned financial corpora from all dataset sources")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--limit",
        type=int,
        default=20000,
        help="Row cap per source to prevent OOM; set 0 for no limit",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Skip remote Hugging Face, URL, zip, and Kaggle sources during this run",
    )
    args = parser.parse_args()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(args.manifest)
    all_records: list[NormalizedRecord] = []
    source_summary: list[dict[str, Any]] = []

    for entry in manifest:
        source_name = entry["name"]
        task_type = entry["task_type"]
        if args.local_only and entry["source_type"] != "local_csv":
            source_summary.append({"source_name": source_name, "status": "skipped", "reason": "local_only"})
            continue
        try:
            frames = collect_frames(entry, limit=args.limit)
        except Exception as exc:
            source_summary.append({"source_name": source_name, "status": "skipped", "reason": str(exc)})
            continue

        source_count = 0
        for frame_name, frame in frames:
            if args.limit > 0:
                frame = frame.head(args.limit)
            records = dataframe_to_records(frame_name, task_type, frame)
            source_count += len(records)
            all_records.extend(records)

        source_summary.append({"source_name": source_name, "status": "ok", "records": source_count})

    deduped: dict[str, NormalizedRecord] = {}
    for record in all_records:
        deduped.setdefault(record.row_hash, record)

    merged_records = list(deduped.values())
    instruction_records = [
        {
            "source_name": record.source_name,
            "task_type": record.task_type,
            "input": record.input_text,
            "output": record.target_text,
            "metadata": record.metadata,
        }
        for record in merged_records
        if record.target_text is not None
    ]
    rag_records = [
        {
            "source_name": record.source_name,
            "task_type": record.task_type,
            "text": record.raw_text,
            "metadata": record.metadata,
        }
        for record in merged_records
    ]

    write_jsonl(
        output_dir / "merged_records.jsonl",
        [record.__dict__ for record in merged_records],
    )
    write_jsonl(output_dir / "instruction_corpus.jsonl", instruction_records)
    write_jsonl(output_dir / "rag_corpus.jsonl", rag_records)
    (output_dir / "summary.json").write_text(
        json.dumps(
            {
                "sources": source_summary,
                "raw_record_count": len(all_records),
                "deduplicated_record_count": len(merged_records),
                "instruction_record_count": len(instruction_records),
                "rag_record_count": len(rag_records),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()