from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import format_error


BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def register(app: FastMCP) -> None:
    """Register RAG-MCP coordinator tools for knowledge base orchestration."""

    @app.tool()
    async def query_knowledge_base_advanced(
        query: str,
        filter_source: str | None = None,
        k: int = 5,
        include_metadata: bool = True,
    ) -> str:
        """
        Advanced query to the FinPath knowledge base with filtering and metadata.
        Used for: comprehensive financial intelligence retrieval, contextual decision support.
        Returns: top-k ranked results with source information and relevance scores.
        
        Args:
            query: The knowledge query or question
            filter_source: Optional filter by source name (e.g., "india_finance", "tax_rules")
            k: Number of top results to return (default: 5)
            include_metadata: Include metadata in results (default: True)
        """
        try:
            import requests
            import json
            
            backend_url = "http://localhost:8000"
            
            payload = {
                "question": query,
                "top_k": max(1, k),
            }
            
            response = requests.post(f"{backend_url}/rag/query", json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                return f"Knowledge Base Query Failed: {result.get('error')}"
            
            results = result.get("results", [])
            
            # Apply source filter if specified
            if filter_source:
                results = [r for r in results if filter_source.lower() in r.get("source", "").lower()]
            
            # Format output
            output_lines = [
                f"Knowledge Base Query: '{query}'",
                f"Results Found: {len(results)}",
                ""
            ]
            
            if not results:
                output_lines.append("No matching knowledge found. Try a different query.")
                return "\n".join(output_lines)
            
            for i, result in enumerate(results[:k], start=1):
                text_snippet = result.get("text", "")[:300]
                if len(result.get("text", "")) > 300:
                    text_snippet += "..."
                
                output_lines.extend([
                    f"{i}. Source: {result.get('source', 'Unknown')}",
                    f"   Relevance: {result.get('similarity', 0.0):.1%}",
                ])
                
                if include_metadata:
                    output_lines.append(f"   Snippet: {text_snippet}")
                
                output_lines.append("")
            
            return "\n".join(output_lines)
            
        except ImportError as e:
            return format_error("query_knowledge_base_advanced", ImportError(f"Required package not installed: {e}"))
        except Exception as err:
            return format_error("query_knowledge_base_advanced", err)

    @app.tool()
    async def add_to_knowledge_base(
        document_text: str,
        source_name: str,
        document_type: str = "manual",
        tags: list[str] | None = None,
    ) -> str:
        """
        Add or update a document in the FinPath knowledge base.
        Used for: continuous knowledge base enrichment, custom financial documents.
        Returns: confirmation with document ID and storage status.
        
        Args:
            document_text: The text content to add to knowledge base
            source_name: Source identifier (e.g., "user_note", "tax_guide_2024")
            document_type: Type of document (manual, news, tax, policy, etc.)
            tags: Optional list of tags for categorization
        """
        try:
            import requests
            import json
            
            backend_url = "http://localhost:8000"
            
            metadata = {
                "source_name": source_name,
                "document_type": document_type,
                "tags": tags or [],
            }
            
            payload = {
                "text": document_text,
                "metadata": metadata,
            }
            
            response = requests.post(f"{backend_url}/rag/upsert", json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "success":
                return (
                    f"✓ Document Added to Knowledge Base\n"
                    f"  Document ID: {result.get('row_id', 'unknown')}\n"
                    f"  Source: {source_name}\n"
                    f"  Type: {document_type}\n"
                    f"  Text Length: {len(document_text)} characters\n"
                    f"  Status: {result.get('message', 'Success')}"
                )
            else:
                return f"Failed to add document: {result.get('error', 'Unknown error')}"
            
        except ImportError as e:
            return format_error("add_to_knowledge_base", ImportError(f"Required package not installed: {e}"))
        except Exception as err:
            return format_error("add_to_knowledge_base", err)

    @app.tool()
    async def get_knowledge_base_status() -> str:
        """
        Get current status and statistics of the FinPath knowledge base.
        Used for: monitoring knowledge base health, understanding coverage.
        Returns: total documents, embedding model, storage info.
        """
        try:
            import requests
            
            backend_url = "http://localhost:8000"
            
            response = requests.get(f"{backend_url}/rag/stats", timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "ok":
                output_lines = [
                    "Knowledge Base Status",
                    "======================",
                    f"Collection: {result.get('collection_name', 'unknown')}",
                    f"Total Documents: {result.get('total_documents', 'unknown')}",
                    f"Embedding Model: {result.get('embedding_model', 'unknown')}",
                    f"Storage Location: {result.get('db_path', 'unknown')}",
                    f"Status: ✓ Operational",
                ]
                return "\n".join(output_lines)
            else:
                return f"Knowledge Base Status: {result.get('message', 'Unknown status')}"
            
        except Exception as err:
            return (
                f"Knowledge Base Status: Unable to connect\n"
                f"Error: {str(err)}\n"
                f"Ensure the backend is running at http://localhost:8000"
            )

    @app.tool()
    async def search_knowledge_by_financial_category(
        category: str,
        subcategory: str | None = None,
        limit: int = 10,
    ) -> str:
        """
        Search knowledge base by financial category for structured queries.
        Used for: tax planning, investment rules, regulation compliance.
        Returns: knowledge grouped by category with actionable insights.
        
        Args:
            category: Main category (tax, investment, banking, insurance, retirement)
            subcategory: Optional subcategory (income_tax, capital_gains, mutual_funds, etc.)
            limit: Maximum results to return (default: 10)
        """
        try:
            import requests
            
            backend_url = "http://localhost:8000"
            
            # Build search query
            if subcategory:
                search_query = f"{category} {subcategory} rules guidelines India"
            else:
                search_query = f"{category} financial planning India"
            
            payload = {
                "question": search_query,
                "top_k": max(1, limit),
            }
            
            response = requests.post(f"{backend_url}/rag/query", json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            results = result.get("results", [])
            
            output_lines = [
                f"Financial Knowledge Search: {category}",
                f"{'/' + subcategory if subcategory else ''}",
                "="*50,
                f"Found {len(results)} relevant knowledge chunks",
                "",
            ]
            
            if not results:
                output_lines.append("No specific knowledge found. Try a different category or consult a financial advisor.")
                return "\n".join(output_lines)
            
            for i, result in enumerate(results[:limit], start=1):
                snippet = result.get("text", "")[:250]
                if len(result.get("text", "")) > 250:
                    snippet += "..."
                
                output_lines.extend([
                    f"{i}. [{result.get('source', 'Unknown')}] Confidence: {result.get('similarity', 0):.0%}",
                    f"   {snippet}",
                    ""
                ])
            
            return "\n".join(output_lines)
            
        except Exception as err:
            return format_error("search_knowledge_by_financial_category", err)
