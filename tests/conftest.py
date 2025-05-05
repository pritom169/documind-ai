"""Shared pytest fixtures for the test suite."""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.documents.models import Collection, Document


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        organisation="TestCorp",
    )


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def collection(user):
    return Collection.objects.create(
        owner=user,
        name="Test Collection",
        description="A test collection for unit tests",
    )


@pytest.fixture
def document(collection):
    return Document.objects.create(
        collection=collection,
        title="test_document.pdf",
        file="documents/2024/01/01/test.pdf",
        file_type="pdf",
        file_size_bytes=1024,
        status=Document.Status.COMPLETED,
        chunk_count=5,
    )


@pytest.fixture
def mock_qdrant():
    with patch("core.vectorstore.qdrant_client.QdrantManager") as mock:
        instance = MagicMock()
        instance.search.return_value = [
            {
                "id": str(uuid.uuid4()),
                "score": 0.92,
                "content": "This is a test document chunk about AI engineering.",
                "metadata": {"document_id": str(uuid.uuid4()), "chunk_index": 0},
            },
            {
                "id": str(uuid.uuid4()),
                "score": 0.87,
                "content": "LangGraph enables multi-agent workflows with state management.",
                "metadata": {"document_id": str(uuid.uuid4()), "chunk_index": 1},
            },
        ]
        instance.ensure_collection.return_value = None
        instance.upsert_vectors.return_value = [str(uuid.uuid4()) for _ in range(2)]
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_llm():
    with patch("core.llm.factory.LLMFactory") as mock:
        chat_model = MagicMock()
        chat_model.invoke.return_value = MagicMock(
            content="This is a test response from the LLM."
        )
        mock.get_chat_model.return_value = chat_model
        mock.get_streaming_model.return_value = chat_model

        embeddings = MagicMock()
        embeddings.embed_query.return_value = [0.1] * 1536
        embeddings.embed_documents.return_value = [[0.1] * 1536, [0.2] * 1536]
        mock.get_embeddings.return_value = embeddings

        yield mock
