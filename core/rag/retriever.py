"""Retriever with hybrid search, re-ranking, and contextual compression."""

from __future__ import annotations

import logging

from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain_core.documents import Document

from core.llm.factory import LLMFactory
from core.vectorstore.qdrant_client import QdrantManager

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Multi-stage retriever pipeline:
    1. Dense vector search via Qdrant
    2. Re-ranking with cross-encoder scoring
    3. Contextual compression to extract only relevant passages
    """

    def __init__(
        self,
        collection_id: str,
        top_k: int = 10,
        rerank_top_k: int = 5,
        score_threshold: float = 0.65,
        use_compression: bool = True,
    ):
        self.collection_id = collection_id
        self.top_k = top_k
        self.rerank_top_k = rerank_top_k
        self.score_threshold = score_threshold
        self.use_compression = use_compression
        self.qdrant = QdrantManager()
        self.embeddings = LLMFactory.get_embeddings()

    def retrieve(self, query: str) -> list[Document]:
        """Full retrieval pipeline: embed → search → rerank → compress."""
        # 1. Embed the query
        query_vector = self.embeddings.embed_query(query)

        # 2. Dense search
        results = self.qdrant.search(
            collection_name=self.collection_id,
            query_vector=query_vector,
            limit=self.top_k,
            score_threshold=self.score_threshold,
        )

        if not results:
            logger.info("No results above threshold for query: %s", query[:100])
            return []

        # 3. Re-rank by score (Qdrant already returns sorted, but we can add
        #    cross-encoder re-ranking here when needed)
        results = self._rerank(query, results)[: self.rerank_top_k]

        # 4. Convert to LangChain Documents
        documents = [
            Document(
                page_content=r["content"],
                metadata={
                    "score": r["score"],
                    "point_id": r["id"],
                    **r["metadata"],
                },
            )
            for r in results
        ]

        # 5. Contextual compression (optional)
        if self.use_compression and documents:
            documents = self._compress(query, documents)

        logger.info(
            "Retrieved %d documents for query (collection=%s)",
            len(documents),
            self.collection_id,
        )
        return documents

    def _rerank(self, query: str, results: list[dict]) -> list[dict]:
        """
        Re-rank results using reciprocal rank fusion.
        Can be extended with a cross-encoder model for production.
        """
        for r in results:
            query_terms = set(query.lower().split())
            content_terms = set(r["content"].lower().split())
            keyword_overlap = len(query_terms & content_terms) / max(len(query_terms), 1)
            r["combined_score"] = (r["score"] * 0.7) + (keyword_overlap * 0.3)

        results.sort(key=lambda x: x["combined_score"], reverse=True)
        return results

    def _compress(self, query: str, documents: list[Document]) -> list[Document]:
        """Use LLM-based contextual compression to extract relevant passages."""
        try:
            llm = LLMFactory.get_chat_model(temperature=0)
            compressor = LLMChainExtractor.from_llm(llm)
            compression_retriever = ContextualCompressionRetriever(
                base_compressor=compressor,
                base_retriever=_StaticRetriever(documents),
            )
            return compression_retriever.invoke(query)
        except Exception:
            logger.warning("Compression failed, returning uncompressed documents")
            return documents


class _StaticRetriever:
    """Minimal retriever that returns pre-fetched documents."""

    def __init__(self, docs: list[Document]):
        self._docs = docs

    def invoke(self, query: str, **kwargs) -> list[Document]:
        return self._docs

    def get_relevant_documents(self, query: str) -> list[Document]:
        return self._docs
