"""API integration tests."""

import pytest
from django.urls import reverse
from rest_framework import status

pytestmark = pytest.mark.django_db


class TestAuthEndpoints:
    def test_register_user(self, api_client):
        response = api_client.post(
            reverse("accounts:register"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password": "strongpass123",
                "password_confirm": "strongpass123",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["username"] == "newuser"

    def test_register_password_mismatch(self, api_client):
        response = api_client.post(
            reverse("accounts:register"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password": "strongpass123",
                "password_confirm": "differentpass",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_obtain_token(self, api_client, user):
        response = api_client.post(
            reverse("accounts:token_obtain"),
            {"username": "testuser", "password": "testpass123"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_profile(self, auth_client, user):
        response = auth_client.get(reverse("accounts:profile"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == user.username


class TestCollectionEndpoints:
    def test_create_collection(self, auth_client):
        response = auth_client.post(
            reverse("documents:collection_list"),
            {"name": "My Collection", "description": "Test"},
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "My Collection"

    def test_list_collections(self, auth_client, collection):
        response = auth_client.get(reverse("documents:collection_list"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_collection_detail(self, auth_client, collection):
        response = auth_client.get(
            reverse("documents:collection_detail", kwargs={"id": collection.id})
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == collection.name

    def test_collection_not_owned(self, api_client, collection, db):
        from apps.accounts.models import User

        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="pass123"
        )
        api_client.force_authenticate(other_user)
        response = api_client.get(
            reverse("documents:collection_detail", kwargs={"id": collection.id})
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDocumentEndpoints:
    def test_list_documents(self, auth_client, document):
        response = auth_client.get(reverse("documents:document_list"))
        assert response.status_code == status.HTTP_200_OK

    def test_document_detail(self, auth_client, document):
        response = auth_client.get(
            reverse("documents:document_detail", kwargs={"id": document.id})
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == document.title


class TestConversationEndpoints:
    def test_create_conversation(self, auth_client, collection):
        response = auth_client.post(
            reverse("conversations:conversation_list"),
            {
                "collection": str(collection.id),
                "title": "Test Chat",
                "agent_mode": "qa",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_list_conversations(self, auth_client):
        response = auth_client.get(reverse("conversations:conversation_list"))
        assert response.status_code == status.HTTP_200_OK


class TestAnalyticsEndpoints:
    def test_usage_summary(self, auth_client):
        response = auth_client.get(reverse("analytics:usage_summary"))
        assert response.status_code == status.HTTP_200_OK
        assert "summary" in response.data
