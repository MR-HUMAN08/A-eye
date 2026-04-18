from __future__ import annotations

import os
from typing import Any

from neo4j import GraphDatabase

from agents.audit import build_audit
from agents.ollama_helper import run_ollama
from rag.rag_engine import engine


def query_graph(query: str, profile: dict, session_id: str) -> dict[str, Any]:
    uri = os.getenv("NEO4J_URI", "").strip()
    user = os.getenv("NEO4J_USER", "").strip()
    password = os.getenv("NEO4J_PASSWORD", "").strip()
    if not uri or not user or not password:
        hits = engine.query(query, k=5)
        ctx = "\n".join([h["text"] for h in hits])
        text = run_ollama("You are Graph Reasoning Fallback Agent.", f"Graph unavailable. Answer using text context:\n{ctx}\nQuestion: {query}")
        audit = build_audit(
            "graph_agent",
            [
                "Step 1: Graph connection parameters missing.",
                "Step 2: Fallback to RAG-only reasoning.",
                "Step 3: Returned explainable text fallback.",
            ],
            [h["metadata"].get("source_name", "unknown") for h in hits],
            "medium",
            "passed",
            session_id=session_id,
        )
        return {
            "cypher_query": None,
            "graph_result": [],
            "explanation": "Graph reasoning is currently unavailable. Here's a text-based answer instead: " + text,
            **audit,
        }

    driver = GraphDatabase.driver(uri, auth=(user, password))
    cypher = run_ollama("You convert natural language to Cypher for finance graph.", f"Question: {query}\nReturn only Cypher.")
    rows = []
    try:
        with driver.session() as s:
            for rec in s.run(cypher):
                rows.append(dict(rec))
    except Exception:
        rows = []
    finally:
        driver.close()

    explanation = run_ollama("You are Graph Explanation Agent.", f"Cypher result: {rows}\nExplain in plain English for the user.")
    audit = build_audit(
        "graph_agent",
        [
            "Step 1: Converted natural language query to Cypher.",
            "Step 2: Executed query against Neo4j and collected rows.",
            "Step 3: Generated plain-English explanation from graph output.",
        ],
        ["neo4j_graph"],
        "medium",
        "passed",
        session_id=session_id,
    )
    return {"cypher_query": cypher, "graph_result": rows, "explanation": explanation, **audit}
