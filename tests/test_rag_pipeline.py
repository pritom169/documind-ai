"""Tests for the RAG pipeline components."""

import pytest
from unittest.mock import patch, MagicMock

from core.rag.chunking import chunk_document


class TestChunking:
    def test_recursive_chunking(self):
        text = "Hello world. " * 200  # ~2600 chars
        chunks = chunk_document(text, chunk_size=500, chunk_overlap=50)
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk["chunk_index"] >= 0
            assert len(chunk["content"]) > 0
            assert chunk["token_count"] > 0
            assert chunk["metadata"]["strategy"] == "recursive"

    def test_markdown_chunking(self):
        text = "# Title\n\nParagraph one.\n\n## Section\n\nParagraph two.\n\n" * 20
        chunks = chunk_document(text, strategy="markdown", chunk_size=200, chunk_overlap=20)
        assert len(chunks) > 1

    def test_small_text_single_chunk(self):
        text = "This is a short document that fits in one chunk."
        chunks = chunk_document(text, chunk_size=500, chunk_overlap=50)
        assert len(chunks) == 1
        assert chunks[0]["content"] == text

    def test_empty_chunks_filtered(self):
        text = "Content.\n\n\n\n\n\n\n\n\nMore content."
        chunks = chunk_document(text, chunk_size=50, chunk_overlap=10)
        for chunk in chunks:
            assert len(chunk["content"].strip()) >= 20

    def test_metadata_preserved(self):
        text = "Test content for metadata. " * 50
        metadata = {"source": "test.pdf", "author": "Test"}
        chunks = chunk_document(text, metadata=metadata, chunk_size=200, chunk_overlap=20)
        assert chunks[0]["metadata"]["source"] == "test.pdf"
        assert chunks[0]["metadata"]["author"] == "Test"


class TestRetriever:
    @patch("core.rag.retriever.QdrantManager")
    @patch("core.rag.retriever.LLMFactory")
    def test_retrieve_returns_documents(self, mock_factory, mock_qdrant_cls):
        from core.rag.retriever import HybridRetriever

        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1] * 1536
        mock_factory.get_embeddings.return_value = mock_embeddings

        mock_qdrant = MagicMock()
        mock_qdrant.search.return_value = [
            {
                "id": "point-1",
                "score": 0.95,
                "content": "Relevant document content",
                "metadata": {"document_id": "doc-1", "chunk_index": 0},
            }
        ]
        mock_qdrant_cls.return_value = mock_qdrant

        retriever = HybridRetriever(
            collection_id="test-collection",
            use_compression=False,
        )
        docs = retriever.retrieve("test query")

        assert len(docs) == 1
        assert docs[0].page_content == "Relevant document content"
        assert docs[0].metadata["score"] == 0.95

    @patch("core.rag.retriever.QdrantManager")
    @patch("core.rag.retriever.LLMFactory")
    def test_retrieve_empty_results(self, mock_factory, mock_qdrant_cls):
        from core.rag.retriever import HybridRetriever

        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1] * 1536
        mock_factory.get_embeddings.return_value = mock_embeddings

        mock_qdrant = MagicMock()
        mock_qdrant.search.return_value = []
        mock_qdrant_cls.return_value = mock_qdrant

        retriever = HybridRetriever(
            collection_id="test-collection",
            use_compression=False,
        )
        docs = retriever.retrieve("irrelevant query")
        assert len(docs) == 0
