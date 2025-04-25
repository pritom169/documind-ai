"""Document models — collections, documents, and chunks."""

import uuid

from django.conf import settings
from django.db import models


class Collection(models.Model):
    """A logical grouping of documents (maps to a Qdrant collection)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="collections"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    document_count = models.PositiveIntegerField(default=0)
    total_chunks = models.PositiveIntegerField(default=0)
    embedding_model = models.CharField(max_length=100, default="text-embedding-3-large")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "collections"
        ordering = ["-updated_at"]
        unique_together = [("owner", "name")]

    def __str__(self):
        return f"{self.name} ({self.document_count} docs)"


class Document(models.Model):
    """An uploaded document to be processed and indexed."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    collection = models.ForeignKey(
        Collection, on_delete=models.CASCADE, related_name="documents"
    )
    title = models.CharField(max_length=500)
    file = models.FileField(upload_to="documents/%Y/%m/%d/")
    file_type = models.CharField(max_length=10)
    file_size_bytes = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    error_message = models.TextField(blank=True)
    chunk_count = models.PositiveIntegerField(default=0)
    processing_time_seconds = models.FloatField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    content_hash = models.CharField(max_length=64, blank=True, help_text="SHA-256 of file content")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "documents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} [{self.status}]"


class DocumentChunk(models.Model):
    """A chunk of a document stored in both Postgres (metadata) and Qdrant (vector)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="chunks"
    )
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    token_count = models.PositiveIntegerField(default=0)
    qdrant_point_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "document_chunks"
        ordering = ["document", "chunk_index"]
        unique_together = [("document", "chunk_index")]

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document.title}"
