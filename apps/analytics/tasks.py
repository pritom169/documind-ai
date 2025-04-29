"""Analytics Celery tasks."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def update_collection_stats() -> dict:
    """Periodic task to refresh cached collection statistics."""
    from apps.documents.models import Collection, Document, DocumentChunk

    updated = 0
    for collection in Collection.objects.all():
        doc_count = collection.documents.filter(status=Document.Status.COMPLETED).count()
        chunk_count = DocumentChunk.objects.filter(document__collection=collection).count()
        if collection.document_count != doc_count or collection.total_chunks != chunk_count:
            collection.document_count = doc_count
            collection.total_chunks = chunk_count
            collection.save(update_fields=["document_count", "total_chunks"])
            updated += 1

    logger.info("Updated stats for %d collections", updated)
    return {"updated": updated}
