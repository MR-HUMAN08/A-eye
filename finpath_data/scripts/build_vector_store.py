#!/usr/bin/env python3
"""Create a persistent ChromaDB vector store from the merged RAG input corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED_DIR = BASE_DIR / "data" / "processed"
DEFAULT_DB_DIR = BASE_DIR / "data" / "chroma_db"
DEFAULT_COLLECTION = "finpath_knowledge"
DEFAULT_MODEL = "all-MiniLM-L6-v2"


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


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 120) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= max_chars:
        return [normalized]

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + max_chars)
        chunks.append(normalized[start:end])
        if end >= len(normalized):
            break
        start = max(0, end - overlap)
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a ChromaDB vector store from the RAG corpus")
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    parser.add_argument("--db-dir", type=Path, default=DEFAULT_DB_DIR)
    parser.add_argument("--collection", type=str, default=DEFAULT_COLLECTION)
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--upsert-batch-size", type=int, default=2000)
    args = parser.parse_args()

    rag_records = read_jsonl(args.processed_dir / "rag_input_corpus.jsonl")
    if not rag_records:
        raise SystemExit("No rag_input_corpus.jsonl found. Run build_rag_input_corpus.py first.")

    model = SentenceTransformer(args.model)
    client = chromadb.PersistentClient(path=str(args.db_dir))
    collection = client.get_or_create_collection(name=args.collection, metadata={"hnsw:space": "cosine"})

    documents: list[str] = []
    ids: list[str] = []
    metadatas: list[dict[str, Any]] = []

    for record in rag_records:
        content = str(record.get("content", "")).strip()
        if not content:
            continue
        chunks = chunk_text(content)
        for chunk_index, chunk in enumerate(chunks):
            document_id = stable_hash(f"{record.get('source_kind')}|{record.get('source_name')}|{record.get('row_hash')}|{chunk_index}")
            documents.append(chunk)
            ids.append(document_id)
            metadatas.append(
                {
                    "source_kind": record.get("source_kind"),
                    "source_name": record.get("source_name"),
                    "document_type": record.get("document_type"),
                    "chunk_index": chunk_index,
                    "row_hash": record.get("row_hash"),
                }
            )

    embeddings = model.encode(documents, show_progress_bar=True, normalize_embeddings=True).tolist()

    batch_size = max(1, args.upsert_batch_size)
    for start in range(0, len(ids), batch_size):
        end = start + batch_size
        collection.upsert(
            ids=ids[start:end],
            documents=documents[start:end],
            embeddings=embeddings[start:end],
            metadatas=metadatas[start:end],
        )

    (args.processed_dir / "vector_store_summary.json").write_text(
        json.dumps(
            {
                "collection": args.collection,
                "model": args.model,
                "document_count": len(documents),
                "record_count": len(rag_records),
                "db_dir": str(args.db_dir),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()