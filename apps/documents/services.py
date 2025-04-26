"""Document processing service — orchestrates ingestion pipeline."""

import hashlib
import logging
import time

from django.db import transaction

from core.rag.chunking import chunk_document
from core.rag.pipeline import RAGPipeline
from core.vectorstore.qdrant_client import QdrantManager

from .models import Document, DocumentChunk

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Handles end-to-end document processing: parse → chunk → embed → store."""

    def __init__(self):
        self.rag_pipeline = RAGPipeline()
        self.qdrant = QdrantManager()

    def process(self, document_id: str) -> None:
        document = Document.objects.select_related("collection").get(id=document_id)
        start_time = time.time()

        try:
            document.status = Document.Status.PROCESSING
            document.save(update_fields=["status"])

            # 1. Compute content hash for deduplication
            content_hash = self._compute_hash(document)
            document.content_hash = content_hash
            document.save(update_fields=["content_hash"])

            # 2. Load and parse document
            raw_text = self.rag_pipeline.load_document(document.file.path, document.file_type)

            # 3. Chunk document
            chunks = chunk_document(raw_text, document.metadata)

            # 4. Generate embeddings
            texts = [c["content"] for c in chunks]
            embeddings = self.rag_pipeline.embed_texts(texts)

            # 5. Store in Qdrant and Postgres
            self._store_chunks(document, chunks, embeddings)

            # 6. Update document and collection stats
            elapsed = time.time() - start_time
            with transaction.atomic():
                document.status = Document.Status.COMPLETED
                document.chunk_count = len(chunks)
                document.processing_time_seconds = round(elapsed, 2)
                document.save(
                    update_fields=["status", "chunk_count", "processing_time_seconds"]
                )

                collection = document.collection
                collection.document_count = collection.documents.filter(
                    status=Document.Status.COMPLETED
                ).count()
                collection.total_chunks = DocumentChunk.objects.filter(
                    document__collection=collection
                ).count()
                collection.save(update_fields=["document_count", "total_chunks"])

            logger.info(
                "Document processed",
                extra={
                    "document_id": str(document.id),
                    "chunks": len(chunks),
                    "time_seconds": round(elapsed, 2),
                },
            )

        except Exception as e:
            document.status = Document.Status.FAILED
            document.error_message = str(e)[:2000]
            document.save(update_fields=["status", "error_message"])
            logger.exception("Document processing failed", extra={"document_id": str(document.id)})
            raise

    def _compute_hash(self, document: Document) -> str:
        sha256 = hashlib.sha256()
        with document.file.open("rb") as f:
            for block in iter(lambda: f.read(8192), b""):
                sha256.update(block)
        return sha256.hexdigest()

    def _store_chunks(
        self,
        document: Document,
        chunks: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        collection_name = str(document.collection.id)
        self.qdrant.ensure_collection(collection_name, len(embeddings[0]))

        point_ids = self.qdrant.upsert_vectors(
            collection_name=collection_name,
            embeddings=embeddings,
            payloads=[
                {
                    "document_id": str(document.id),
                    "collection_id": str(document.collection.id),
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    **chunk.get("metadata", {}),
                }
                for chunk in chunks
            ],
        )

        chunk_objects = [
            DocumentChunk(
                document=document,
                chunk_index=chunk["chunk_index"],
                content=chunk["content"],
                token_count=chunk.get("token_count", 0),
                qdrant_point_id=point_ids[i],
                metadata=chunk.get("metadata", {}),
            )
            for i, chunk in enumerate(chunks)
        ]
        DocumentChunk.objects.bulk_create(chunk_objects)
