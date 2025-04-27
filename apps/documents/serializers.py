"""Document serializers."""

from django.conf import settings
from rest_framework import serializers

from .models import Collection, Document, DocumentChunk


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = [
            "id",
            "name",
            "description",
            "is_public",
            "document_count",
            "total_chunks",
            "embedding_model",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "document_count", "total_chunks", "created_at", "updated_at"]


class DocumentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentChunk
        fields = ["id", "chunk_index", "content", "token_count", "metadata"]


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            "id",
            "collection",
            "title",
            "file",
            "file_type",
            "file_size_bytes",
            "status",
            "error_message",
            "chunk_count",
            "processing_time_seconds",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "file_type",
            "file_size_bytes",
            "status",
            "error_message",
            "chunk_count",
            "processing_time_seconds",
            "created_at",
            "updated_at",
        ]


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    collection_id = serializers.UUIDField()
    title = serializers.CharField(max_length=500, required=False)
    metadata = serializers.JSONField(required=False, default=dict)

    def validate_file(self, value):
        ext = value.name.rsplit(".", 1)[-1].lower()
        if ext not in settings.SUPPORTED_FILE_TYPES:
            raise serializers.ValidationError(
                f"Unsupported file type '.{ext}'. Supported: {settings.SUPPORTED_FILE_TYPES}"
            )
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if value.size > max_bytes:
            raise serializers.ValidationError(
                f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit."
            )
        return value

    def validate_collection_id(self, value):
        user = self.context["request"].user
        if not Collection.objects.filter(id=value, owner=user).exists():
            raise serializers.ValidationError("Collection not found.")
        return value
