from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class BackendRAGEngine:
    def __init__(self) -> None:
        base = Path(__file__).resolve().parents[1]
        db_path = os.getenv("CHROMA_DB_PATH", "../../finpath_data/data/chroma_db")
        self.db_path = str((base / db_path).resolve())
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.collection = self.client.get_or_create_collection(name="finpath_knowledge")
        self.embed_model = SentenceTransformer("all-MiniLM-L6-v2")

    def query(self, text: str, k: int = 6) -> list[dict[str, Any]]:
        emb = self.embed_model.encode([text], normalize_embeddings=True).tolist()[0]
        result = self.collection.query(query_embeddings=[emb], n_results=k)
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]
        hits = []
        for doc, meta, dist in zip(docs, metas, dists):
            hits.append({"text": doc, "metadata": meta or {}, "distance": float(dist)})
        return hits

    def upsert_text(self, text: str, metadata: dict[str, Any]) -> str:
        emb = self.embed_model.encode([text], normalize_embeddings=True).tolist()[0]
        row_id = str(uuid.uuid4())
        self.collection.upsert(ids=[row_id], documents=[text], embeddings=[emb], metadatas=[metadata])
        return row_id


engine = BackendRAGEngine()
