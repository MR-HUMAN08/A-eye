#!/usr/bin/env python3
"""Agentic FinPath runtime with dual-role reasoning and self-learning RAG."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
import requests
from sentence_transformers import SentenceTransformer


DEFAULT_DB_DIR = Path("/home/harini/cbit/finpath_data/data/chroma_db")
DEFAULT_COLLECTION = "finpath_knowledge"
DEFAULT_EMBED_MODEL = "all-MiniLM-L6-v2"
DEFAULT_OLLAMA = "http://localhost:11434/api/generate"
DEFAULT_QWEN_MODEL = "qwen2.5:7b"


COMPANY_CFO_SYSTEM = (
    "You are FinPath CFO Agent. Provide strategic financial analysis for a company: "
    "variance analysis, cash-flow forecasting, and risk-aware recommendations. "
    "Always include assumptions and action items."
)

PERSONAL_FINANCE_SYSTEM = (
    "You are FinPath Personal Finance Agent for Indian users. Coach behavior, calculate goal "
    "impact, and give portfolio/tax guidance in simple language using INR context."
)


@dataclass
class RetrievalHit:
    text: str
    metadata: dict[str, Any]
    distance: float


class FinPathRAGEngine:
    def __init__(
        self,
        db_dir: Path = DEFAULT_DB_DIR,
        collection_name: str = DEFAULT_COLLECTION,
        embed_model_name: str = DEFAULT_EMBED_MODEL,
        verbose: bool = True,
    ) -> None:
        self.verbose = verbose
        self._log(f"Loading embedding model: {embed_model_name}")
        self.embed_model = SentenceTransformer(embed_model_name)
        self._log(f"Opening ChromaDB at: {db_dir}")
        self.client = chromadb.PersistentClient(path=str(db_dir))
        self.collection = self.client.get_or_create_collection(name=collection_name)
        self._log(f"Using collection: {collection_name}")

    def _log(self, message: str) -> None:
        if self.verbose:
            print(f"[finpath-rag] {message}", file=sys.stderr, flush=True)

    @staticmethod
    def _hash_text(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def retrieve(self, query: str, k: int = 6) -> list[RetrievalHit]:
        self._log(f"Embedding query and retrieving top-{k} hits")
        query_embedding = self.embed_model.encode([query], normalize_embeddings=True).tolist()[0]
        result = self.collection.query(query_embeddings=[query_embedding], n_results=k)

        hits: list[RetrievalHit] = []
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for doc, meta, dist in zip(docs, metas, distances):
            hits.append(RetrievalHit(text=doc, metadata=meta or {}, distance=float(dist)))
        self._log(f"Retrieved {len(hits)} hits")
        return hits

    def supports_answer(self, hits: list[RetrievalHit], max_distance: float = 0.65) -> bool:
        if not hits:
            return False
        return min(hit.distance for hit in hits) <= max_distance

    def add_knowledge(self, problem: str, resolution: str, source_tag: str = "self_learning") -> str:
        payload = {
            "problem": problem.strip(),
            "resolution": resolution.strip(),
            "source_tag": source_tag,
            "created_at": int(time.time()),
        }
        text = json.dumps(payload, ensure_ascii=False)
        row_id = self._hash_text(text)

        existing = self.collection.get(ids=[row_id])
        if existing and existing.get("ids"):
            return row_id

        embedding = self.embed_model.encode([text], normalize_embeddings=True).tolist()[0]
        self.collection.add(
            ids=[row_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[{"source_kind": "self_learning", "document_type": "edge_case"}],
        )
        return row_id


class FinPathAgentOrchestrator:
    def __init__(
        self,
        rag: FinPathRAGEngine,
        ollama_endpoint: str = DEFAULT_OLLAMA,
        model: str = DEFAULT_QWEN_MODEL,
        ollama_timeout: int = 120,
        max_tokens: int = 512,
        verbose: bool = True,
    ) -> None:
        self.rag = rag
        self.ollama_endpoint = ollama_endpoint
        self.model = model
        self.ollama_timeout = ollama_timeout
        self.max_tokens = max_tokens
        self.verbose = verbose

    def _log(self, message: str) -> None:
        if self.verbose:
            print(f"[finpath-agent] {message}", file=sys.stderr, flush=True)

    def _build_system_prompt(self, mode: str) -> str:
        if mode == "company_cfo":
            return COMPANY_CFO_SYSTEM
        return PERSONAL_FINANCE_SYSTEM

    def _call_ollama(self, system_prompt: str, user_prompt: str) -> str:
        prompt = f"System:\n{system_prompt}\n\nUser:\n{user_prompt}\n\nAssistant:"
        self._log(f"Calling Ollama model={self.model} timeout={self.ollama_timeout}s")
        response = requests.post(
            self.ollama_endpoint,
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": self.max_tokens},
            },
            timeout=(10, self.ollama_timeout),
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()

    def run(self, query: str, mode: str = "personal_finance", retrieval_k: int = 8) -> dict[str, Any]:
        self._log("Starting retrieval")
        hits = self.rag.retrieve(query=query, k=retrieval_k)
        context_blocks = []
        citations = []

        for index, hit in enumerate(hits, start=1):
            source = hit.metadata.get("source_name", "unknown_source")
            doc_type = hit.metadata.get("document_type", "unknown_type")
            context_blocks.append(f"[DOC-{index}] ({source}/{doc_type}) {hit.text}")
            citations.append(f"DOC-{index}:{source}:{doc_type}")

        context = "\n\n".join(context_blocks) if context_blocks else "No retrieval context found."
        support_ok = self.rag.supports_answer(hits)

        user_prompt = (
            f"Question: {query}\n\n"
            f"Retrieved Context:\n{context}\n\n"
            "Instructions:\n"
            "1) Answer in plain language.\n"
            "2) Include a concise reasoning chain.\n"
            "3) Include cited source references using DOC tags.\n"
            "4) For personal finance mode, include practical next steps in INR context.\n"
            "5) If context is weak, explicitly say uncertainty."
        )

        try:
            answer = self._call_ollama(self._build_system_prompt(mode), user_prompt)
        except requests.Timeout:
            answer = (
                "The model call timed out before a final answer was generated. "
                "Please retry with a simpler question or increase --ollama-timeout."
            )
            support_ok = False
        except requests.RequestException as exc:
            answer = f"Model call failed: {exc}"
            support_ok = False
        if not support_ok:
            answer += "\n\nI'm less certain about this."

        audit_trace = {
            "mode": mode,
            "query": query,
            "citations": citations,
            "top_distances": [round(hit.distance, 4) for hit in hits[:5]],
            "hallucination_guard": "pass" if support_ok else "warn",
        }

        return {"answer": answer, "audit_trace": audit_trace}


def main() -> None:
    parser = argparse.ArgumentParser(description="FinPath agentic runtime (dual-role CFO + personal advisor)")
    parser.add_argument("--mode", choices=["company_cfo", "personal_finance"], default="personal_finance")
    parser.add_argument("--query", required=True)
    parser.add_argument("--learn-problem", default="")
    parser.add_argument("--learn-resolution", default="")
    parser.add_argument("--ollama-timeout", type=int, default=120)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--retrieval-k", type=int, default=8)
    parser.add_argument("--quiet", action="store_true", help="Disable progress logs")
    args = parser.parse_args()

    verbose = not args.quiet
    rag = FinPathRAGEngine(verbose=verbose)
    orchestrator = FinPathAgentOrchestrator(
        rag=rag,
        ollama_timeout=args.ollama_timeout,
        max_tokens=args.max_tokens,
        verbose=verbose,
    )

    if args.learn_problem and args.learn_resolution:
        row_id = rag.add_knowledge(problem=args.learn_problem, resolution=args.learn_resolution)
        print(json.dumps({"self_learning_id": row_id}, ensure_ascii=False, indent=2))

    result = orchestrator.run(query=args.query, mode=args.mode, retrieval_k=args.retrieval_k)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
