"""Conversation REST API views (non-streaming)."""

import logging
import time

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.documents.models import Collection
from core.agents.graph import run_agent_graph

from .models import Conversation, Message
from .serializers import (
    ChatRequestSerializer,
    ConversationDetailSerializer,
    ConversationSerializer,
)

logger = logging.getLogger(__name__)


class ConversationListCreateView(generics.ListCreateAPIView):
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user, is_archived=False)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ConversationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ConversationDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat(request):
    """Synchronous chat endpoint — sends a message and returns the full response."""
    serializer = ChatRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    user = request.user
    if not user.has_quota():
        return Response(
            {"detail": "Monthly API quota exceeded."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # Get or create conversation
    conversation = _get_or_create_conversation(user, data)

    # Save user message
    user_msg = Message.objects.create(
        conversation=conversation,
        role=Message.Role.USER,
        content=data["message"],
    )

    # Build conversation history
    history = list(
        conversation.messages.order_by("created_at").values_list("role", "content")
    )

    # Determine collection for RAG
    collection_id = str(conversation.collection_id) if conversation.collection_id else None

    # Run agent graph
    start = time.time()
    result = run_agent_graph(
        query=data["message"],
        history=[(r, c) for r, c in history],
        collection_id=collection_id,
        agent_mode=conversation.agent_mode,
        user_id=str(user.id),
    )
    latency_ms = int((time.time() - start) * 1000)

    # Save assistant message
    assistant_msg = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content=result["answer"],
        sources=result.get("sources", []),
        model_used=result.get("model", ""),
        latency_ms=latency_ms,
        metadata=result.get("metadata", {}),
    )

    user.increment_usage()

    return Response(
        {
            "conversation_id": str(conversation.id),
            "message": {
                "id": str(assistant_msg.id),
                "content": assistant_msg.content,
                "sources": assistant_msg.sources,
                "model_used": assistant_msg.model_used,
                "latency_ms": latency_ms,
            },
        }
    )


def _get_or_create_conversation(user, data: dict) -> Conversation:
    if data.get("conversation_id"):
        return Conversation.objects.get(id=data["conversation_id"], user=user)

    kwargs = {
        "user": user,
        "agent_mode": data.get("agent_mode", "qa"),
        "title": data["message"][:100],
    }
    if data.get("collection_id"):
        kwargs["collection"] = Collection.objects.get(id=data["collection_id"], owner=user)

    return Conversation.objects.create(**kwargs)
