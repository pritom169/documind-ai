"""Celery tasks for asynchronous document processing."""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def process_document_task(self, document_id: str) -> dict:
    """Process a document asynchronously: parse, chunk, embed, store."""
    from .services import DocumentProcessor

    try:
        processor = DocumentProcessor()
        processor.process(document_id)
        return {"status": "completed", "document_id": document_id}
    except Exception as exc:
        logger.exception("Document processing task failed", extra={"document_id": document_id})
        raise self.retry(exc=exc)


@shared_task
def cleanup_expired_documents() -> dict:
    """Remove documents older than retention period."""
    from .models import Document

    cutoff = timezone.now() - timezone.timedelta(days=90)
    expired = Document.objects.filter(
        created_at__lt=cutoff,
        collection__metadata__auto_cleanup=True,
    )
    count = expired.count()
    expired.delete()

    logger.info("Cleaned up %d expired documents", count)
    return {"deleted": count}


@shared_task(bind=True, max_retries=2)
def reindex_collection_task(self, collection_id: str) -> dict:
    """Re-process all documents in a collection."""
    from .models import Document

    documents = Document.objects.filter(
        collection_id=collection_id,
        status=Document.Status.COMPLETED,
    )
    for doc in documents:
        process_document_task.delay(str(doc.id))

    return {"collection_id": collection_id, "reindexed": documents.count()}
