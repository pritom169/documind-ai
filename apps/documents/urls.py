"""Document URL patterns."""

from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    # Collections
    path("collections/", views.CollectionListCreateView.as_view(), name="collection_list"),
    path("collections/<uuid:id>/", views.CollectionDetailView.as_view(), name="collection_detail"),
    path(
        "collections/<uuid:collection_id>/reindex/",
        views.reindex_collection,
        name="collection_reindex",
    ),
    # Documents
    path("", views.DocumentListView.as_view(), name="document_list"),
    path("<uuid:id>/", views.DocumentDetailView.as_view(), name="document_detail"),
    path("upload/", views.upload_document, name="document_upload"),
    # Chunks
    path("<uuid:document_id>/chunks/", views.DocumentChunkListView.as_view(), name="chunk_list"),
]
