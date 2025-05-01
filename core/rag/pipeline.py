"""End-to-end RAG pipeline — document loading, embedding, and querying."""

from __future__ import annotations

import logging
from pathlib import Path

from langchain_community.document_loaders import (
    CSVLoader,
    JSONLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredHTMLLoader,
    UnstructuredWordDocumentLoader,
)

from core.llm.factory import LLMFactory

logger = logging.getLogger(__name__)

LOADER_MAP = {
    "pdf": PyPDFLoader,
    "txt": TextLoader,
    "md": TextLoader,
    "csv": CSVLoader,
    "json": JSONLoader,
    "html": UnstructuredHTMLLoader,
    "docx": UnstructuredWordDocumentLoader,
}


class RAGPipeline:
    """Orchestrates document loading and embedding generation."""

    def __init__(self, provider_name: str | None = None):
        self.provider_name = provider_name
        self._embeddings = None

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = LLMFactory.get_embeddings(self.provider_name)
        return self._embeddings

    def load_document(self, file_path: str, file_type: str) -> str:
        """Load and extract text from a document file."""
        loader_cls = LOADER_MAP.get(file_type)
        if loader_cls is None:
            raise ValueError(f"Unsupported file type: {file_type}")

        kwargs = {"file_path": file_path}
        if file_type == "json":
            kwargs["jq_schema"] = "."
            kwargs["text_content"] = False

        loader = loader_cls(**kwargs)
        documents = loader.load()

        full_text = "\n\n".join(doc.page_content for doc in documents)
        logger.info(
            "Loaded document: %s (%d chars, %d pages/sections)",
            Path(file_path).name,
            len(full_text),
            len(documents),
        )
        return full_text

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of text chunks."""
        # Batch to avoid rate limits
        batch_size = 50
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings = self.embeddings.embed_documents(batch)
            all_embeddings.extend(embeddings)

        logger.info("Generated %d embeddings", len(all_embeddings))
        return all_embeddings

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a single query."""
        return self.embeddings.embed_query(query)
