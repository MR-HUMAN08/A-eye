from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
import pandas as pd
import pdfplumber

from agents.audit import build_audit
from agents.ollama_helper import run_ollama
from rag.rag_engine import engine


def process_upload(filename: str, content: bytes, session_id: str) -> dict:
    lower = filename.lower()
    summaries = []
    chunks = []

    if lower.endswith(".pdf"):
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for idx, page in enumerate(pdf.pages, start=1):
                text = (page.extract_text() or "").strip()
                if text:
                    chunks.append(text)
                    s = run_ollama("You are Document Intelligence Agent.", f"Summarize page {idx} and mention table/figure implications:\n{text[:2500]}")
                    summaries.append({"page": idx, "summary": s})
    elif lower.endswith(".xlsx") or lower.endswith(".xls"):
        book = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        for sheet_name in book.sheetnames:
            ws = book[sheet_name]
            rows = list(ws.values)
            if not rows:
                continue
            df = pd.DataFrame(rows[1:], columns=[str(c) for c in rows[0]])
            numeric = df.select_dtypes(include="number")
            stats = {}
            for col in numeric.columns:
                stats[col] = {"min": float(numeric[col].min()), "max": float(numeric[col].max()), "mean": float(numeric[col].mean())}
            txt = f"Sheet {sheet_name} columns: {list(df.columns)}. Stats: {stats}"
            chunks.append(txt)
            summaries.append({"sheet": sheet_name, "summary": txt})
    else:
        return {"filename": filename, "error": "Unsupported file type", **build_audit("document_intelligence_agent", ["Step 1: File type validation failed."], [], "low", "flagged", session_id=session_id)}

    indexed = 0
    for ch in chunks:
        engine.upsert_text(
            ch,
            {
                "source": filename,
                "source_name": filename,
                "type": "user_uploaded",
                "upload_timestamp": datetime.now(timezone.utc).isoformat(),
                "document_type": "user_upload",
            },
        )
        indexed += 1

    relevance_hits = engine.query("house goal savings Hyderabad 5 years", k=3)
    relevance_text = "\n".join([h["text"] for h in relevance_hits])
    goal_relevance = run_ollama("You are Goal Relevance Analyzer.", f"Explain what this document means for the user's financial goal:\n{relevance_text}")
    reasoning = [
        "Step 1: Extracted content from uploaded document pages/sheets.",
        "Step 2: Summarized extracted content and indexed chunks into ChromaDB.",
        "Step 3: Retrieved top goal-relevance chunks and generated impact explanation.",
    ]
    sources = [filename] + [h["metadata"].get("source_name", "unknown") for h in relevance_hits]
    audit = build_audit("document_intelligence_agent", reasoning, sources, "medium", "passed", session_id=session_id)
    return {
        "filename": filename,
        "pages_processed": len(summaries),
        "summary": summaries,
        "goal_relevance": goal_relevance,
        "chunks_indexed": indexed,
        **audit,
    }
