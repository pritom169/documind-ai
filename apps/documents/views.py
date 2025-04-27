"""Document and collection API views."""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Collection, Document, DocumentChunk
from .serializers import (
    CollectionSerializer,
    DocumentChunkSerializer,
    DocumentSerializer,
    DocumentUploadSerializer,
)
from .tasks import process_document_task, reindex_collection_task


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------


class CollectionListCreateView(generics.ListCreateAPIView):
    serializer_class = CollectionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["is_public"]

    def get_queryset(self):
        return Collection.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class CollectionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CollectionSerializer
    lookup_field = "id"

    def get_queryset(self):
        return Collection.objects.filter(owner=self.request.user)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


class DocumentListView(generics.ListAPIView):
    serializer_class = DocumentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "collection"]

    def get_queryset(self):
        return Document.objects.filter(collection__owner=self.request.user)


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = DocumentSerializer
    lookup_field = "id"

    def get_queryset(self):
        return Document.objects.filter(collection__owner=self.request.user)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def upload_document(request):
    """Upload and queue a document for processing."""
    serializer = DocumentUploadSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)

    uploaded_file = serializer.validated_data["file"]
    collection = Collection.objects.get(id=serializer.validated_data["collection_id"])

    document = Document.objects.create(
        collection=collection,
        title=serializer.validated_data.get("title", uploaded_file.name),
        file=uploaded_file,
        file_type=uploaded_file.name.rsplit(".", 1)[-1].lower(),
        file_size_bytes=uploaded_file.size,
        metadata=serializer.validated_data.get("metadata", {}),
    )

    process_document_task.delay(str(document.id))

    return Response(
        DocumentSerializer(document).data,
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def reindex_collection(request, collection_id):
    """Trigger re-indexing of all documents in a collection."""
    if not Collection.objects.filter(id=collection_id, owner=request.user).exists():
        return Response({"detail": "Collection not found."}, status=status.HTTP_404_NOT_FOUND)

    reindex_collection_task.delay(str(collection_id))
    return Response({"detail": "Re-indexing started."}, status=status.HTTP_202_ACCEPTED)


# ---------------------------------------------------------------------------
# Chunks (read-only)
# ---------------------------------------------------------------------------


class DocumentChunkListView(generics.ListAPIView):
    serializer_class = DocumentChunkSerializer

    def get_queryset(self):
        return DocumentChunk.objects.filter(
            document_id=self.kwargs["document_id"],
            document__collection__owner=self.request.user,
        )
