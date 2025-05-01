"""Advanced document chunking strategies using LangChain text splitters."""

from __future__ import annotations

import logging
import re

from django.conf import settings
from langchain_text_splitters import (
    MarkdownTextSplitter,
    RecursiveCharacterTextSplitter,
    TokenTextSplitter,
)

logger = logging.getLogger(__name__)


def chunk_document(
    text: str,
    metadata: dict | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    strategy: str = "recursive",
) -> list[dict]:
    """
    Split a document into chunks using the specified strategy.

    Strategies:
        - recursive: RecursiveCharacterTextSplitter (best general purpose)
        - markdown:  MarkdownTextSplitter (structure-aware for .md)
        - token:     TokenTextSplitter (exact token boundaries)
        - semantic:  Paragraph-based splitting with context windows

    Returns list of dicts with keys: chunk_index, content, token_count, metadata.
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
    metadata = metadata or {}

    splitter = _get_splitter(strategy, chunk_size, chunk_overlap)
    raw_chunks = splitter.split_text(text)

    chunks = []
    for i, content in enumerate(raw_chunks):
        content = _clean_chunk(content)
        if len(content.strip()) < 20:
            continue

        token_count = _estimate_tokens(content)

        chunks.append(
            {
                "chunk_index": i,
                "content": content,
                "token_count": token_count,
                "metadata": {
                    **metadata,
                    "strategy": strategy,
                    "char_count": len(content),
                },
            }
        )

    logger.info(
        "Chunked document: %d chunks (strategy=%s, size=%d, overlap=%d)",
        len(chunks),
        strategy,
        chunk_size,
        chunk_overlap,
    )
    return chunks


def _get_splitter(strategy: str, chunk_size: int, chunk_overlap: int):
    if strategy == "markdown":
        return MarkdownTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    elif strategy == "token":
        return TokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    else:
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )


def _clean_chunk(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def _estimate_tokens(text: str) -> int:
    return len(text) // 4
