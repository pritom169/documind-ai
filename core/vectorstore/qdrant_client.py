"""Qdrant vector store manager with connection pooling."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from django.conf import settings
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

logger = logging.getLogger(__name__)


class QdrantManager:
    """Manages Qdrant collections, upserts, and queries."""

    _client: QdrantClient | None = None

    @classmethod
    def get_client(cls) -> QdrantClient:
        if cls._client is None:
            kwargs: dict[str, Any] = {
                "host": settings.QDRANT_HOST,
                "port": settings.QDRANT_PORT,
                "grpc_port": settings.QDRANT_GRPC_PORT,
                "prefer_grpc": True,
            }
            if settings.QDRANT_API_KEY:
                kwargs["api_key"] = settings.QDRANT_API_KEY
            cls._client = QdrantClient(**kwargs)
            logger.info("Qdrant client initialised (%s:%s)", settings.QDRANT_HOST, settings.QDRANT_PORT)
        return cls._client

    def ensure_collection(self, collection_name: str, vector_size: int) -> None:
        client = self.get_client()
        collections = [c.name for c in client.get_collections().collections]
        if collection_name not in collections:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection: %s (dim=%d)", collection_name, vector_size)

    def upsert_vectors(
        self,
        collection_name: str,
        embeddings: list[list[float]],
        payloads: list[dict[str, Any]],
    ) -> list[str]:
        client = self.get_client()
        point_ids = [str(uuid.uuid4()) for _ in embeddings]

        points = [
            PointStruct(id=pid, vector=emb, payload=payload)
            for pid, emb, payload in zip(point_ids, embeddings, payloads)
        ]

        # Batch upsert (100 points per batch)
        batch_size = 100
        for i in range(0, len(points), batch_size):
            client.upsert(
                collection_name=collection_name,
                points=points[i : i + batch_size],
            )

        logger.info("Upserted %d vectors to %s", len(points), collection_name)
        return point_ids

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 5,
        score_threshold: float = 0.7,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[dict]:
        client = self.get_client()

        qdrant_filter = None
        if filter_conditions:
            must = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filter_conditions.items()
            ]
            qdrant_filter = Filter(must=must)

        results = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=qdrant_filter,
        )

        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "content": hit.payload.get("content", ""),
                "metadata": {
                    k: v for k, v in hit.payload.items() if k != "content"
                },
            }
            for hit in results
        ]

    def delete_by_document(self, collection_name: str, document_id: str) -> None:
        client = self.get_client()
        client.delete(
            collection_name=collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
        )
        logger.info("Deleted vectors for document %s from %s", document_id, collection_name)

    def delete_collection(self, collection_name: str) -> None:
        client = self.get_client()
        client.delete_collection(collection_name)
        logger.info("Deleted Qdrant collection: %s", collection_name)

    def get_collection_info(self, collection_name: str) -> dict:
        client = self.get_client()
        info = client.get_collection(collection_name)
        return {
            "name": collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status.value,
        }
