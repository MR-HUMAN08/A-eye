from __future__ import annotations

import json
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP


BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from rag.rag_engine import engine  # noqa: E402


def register(app: FastMCP) -> None:
    @app.resource(
        "finpath://user/demo-profile",
        mime_type="text/markdown",
        description=(
            "Current demo user's financial profile. "
            "Driven by dynamic runtime context from frontend/demo inputs."
        ),
    )
    def demo_profile_resource() -> str:
        profile_path = BACKEND_ROOT / "default_profile.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        return (
            "# Demo User Financial Profile\n\n"
            f"- Name: {profile.get('name', 'n/a')}\n"
            f"- Age: {profile.get('age', 'n/a')}\n"
            f"- Monthly Income: INR {profile.get('monthly_income', 'n/a')}\n"
            f"- Goal: {profile.get('goal', 'n/a')}\n"
            f"- Timeline: {profile.get('goal_timeline_years', 'n/a')} years\n"
            f"- Risk Appetite: {profile.get('risk_appetite', 'n/a')}\n"
            f"- Existing Savings: INR {profile.get('existing_savings', 'n/a')}\n"
        )

    @app.resource(
        "finpath://knowledge/india-finance",
        mime_type="text/plain",
        description=(
            "FinPath's India-specific financial knowledge base. Covers SIP/ELSS/PPF/SGB/NPS instruments, "
            "Hyderabad real estate prices, tax brackets, spending benchmarks for INR 60k/month income, "
            "and behavioral finance patterns."
        ),
    )
    def india_finance_resource() -> str:
        kb_path = BACKEND_ROOT / "rag" / "india_finance_knowledge.txt"
        return kb_path.read_text(encoding="utf-8")

    @app.resource(
        "finpath://knowledge/rag-stats",
        mime_type="application/json",
        description=(
            "Live stats from FinPath's RAG vector store - 8,662 chunks from 7 source repositories including "
            "Anthropic financial-services-plugins, FinGPT, and Hybrid-Graph-RAG."
        ),
    )
    def rag_stats_resource() -> str:
        count = engine.collection.count()
        records = engine.collection.get(include=["metadatas"]) if count > 0 else {"metadatas": []}
        metadatas = records.get("metadatas", []) or []
        source_set = set()
        for meta in metadatas:
            if isinstance(meta, dict):
                source_set.add(meta.get("source_name") or meta.get("source") or "unknown")
        payload = {
            "collection": "finpath_knowledge",
            "total_chunks": count,
            "embedding_model": "all-MiniLM-L6-v2",
            "source_documents": sorted(source_set),
            "db_path": engine.db_path,
        }
        return json.dumps(payload, indent=2)
