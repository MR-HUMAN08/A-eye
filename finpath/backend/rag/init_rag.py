from __future__ import annotations

from pathlib import Path

from rag.rag_engine import engine


def main() -> None:
    kb_path = Path(__file__).resolve().parent / "india_finance_knowledge.txt"
    text = kb_path.read_text(encoding="utf-8")
    chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
    for chunk in chunks:
        engine.upsert_text(chunk, {"source_name": "india_finance_knowledge.txt", "document_type": "kb"})
    print(f"Indexed {len(chunks)} chunks")


if __name__ == "__main__":
    main()
