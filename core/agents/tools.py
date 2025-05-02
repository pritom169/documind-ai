"""Custom tools available to LangGraph agents."""

from __future__ import annotations

import logging

from langchain_core.tools import tool

from core.rag.retriever import HybridRetriever
from core.vectorstore.qdrant_client import QdrantManager

logger = logging.getLogger(__name__)


@tool
def search_documents(query: str, collection_id: str, top_k: int = 5) -> str:
    """Search through uploaded documents using semantic similarity.

    Args:
        query: The search query.
        collection_id: UUID of the document collection to search.
        top_k: Number of results to return.
    """
    retriever = HybridRetriever(
        collection_id=collection_id,
        rerank_top_k=top_k,
        use_compression=False,
    )
    docs = retriever.retrieve(query)

    if not docs:
        return "No relevant documents found."

    results = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("document_id", "unknown")
        score = doc.metadata.get("score", 0)
        results.append(f"[{i}] (score: {score:.2f}, doc: {source})\n{doc.page_content}")

    return "\n\n---\n\n".join(results)


@tool
def get_collection_info(collection_id: str) -> str:
    """Get information about a document collection.

    Args:
        collection_id: UUID of the collection.
    """
    qdrant = QdrantManager()
    try:
        info = qdrant.get_collection_info(collection_id)
        return (
            f"Collection: {info['name']}\n"
            f"Vectors: {info['vectors_count']}\n"
            f"Points: {info['points_count']}\n"
            f"Status: {info['status']}"
        )
    except Exception as e:
        return f"Could not retrieve collection info: {e}"


@tool
def multi_query_search(queries: list[str], collection_id: str, top_k: int = 3) -> str:
    """Run multiple search queries and combine results for broader coverage.

    Args:
        queries: List of search queries to run.
        collection_id: UUID of the document collection.
        top_k: Results per query.
    """
    retriever = HybridRetriever(
        collection_id=collection_id,
        rerank_top_k=top_k,
        use_compression=False,
    )

    all_results = {}
    for query in queries:
        docs = retriever.retrieve(query)
        for doc in docs:
            point_id = doc.metadata.get("point_id", "")
            if point_id not in all_results:
                all_results[point_id] = doc

    # Sort by score
    sorted_docs = sorted(
        all_results.values(),
        key=lambda d: d.metadata.get("score", 0),
        reverse=True,
    )

    if not sorted_docs:
        return "No relevant documents found across all queries."

    results = []
    for i, doc in enumerate(sorted_docs[:top_k * 2], 1):
        score = doc.metadata.get("score", 0)
        results.append(f"[{i}] (score: {score:.2f})\n{doc.page_content}")

    return "\n\n---\n\n".join(results)


AGENT_TOOLS = [search_documents, get_collection_info, multi_query_search]
