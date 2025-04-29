"""Analytics models for tracking platform usage."""

import uuid

from django.conf import settings
from django.db import models


class UsageEvent(models.Model):
    """Tracks individual API usage events for observability."""

    class EventType(models.TextChoices):
        QUERY = "query", "Query"
        DOCUMENT_UPLOAD = "document_upload", "Document Upload"
        DOCUMENT_PROCESS = "document_process", "Document Processing"
        EMBEDDING = "embedding", "Embedding Generation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="usage_events"
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    model_used = models.CharField(max_length=100, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "usage_events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
        ]
