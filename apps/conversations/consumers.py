"""WebSocket consumer for streaming AI responses."""

import json
import logging
import time

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebSocketConsumer

from apps.accounts.models import User
from apps.documents.models import Collection
from core.agents.graph import astream_agent_graph

from .models import Conversation, Message

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebSocketConsumer):
    """WebSocket consumer that streams LangGraph agent responses token-by-token."""

    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        self.conversation_id = self.scope["url_route"]["kwargs"].get("conversation_id")
        self.room_group = f"chat_{self.conversation_id or self.user.id}"

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group"):
            await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON")
            return

        message = data.get("message", "").strip()
        if not message:
            await self.send_error("Empty message")
            return

        # Check quota
        has_quota = await self._check_quota()
        if not has_quota:
            await self.send_error("Monthly API quota exceeded")
            return

        collection_id = data.get("collection_id")
        agent_mode = data.get("agent_mode", "qa")

        # Get or create conversation
        conversation = await self._get_or_create_conversation(
            message, collection_id, agent_mode
        )

        # Save user message
        await self._save_message(conversation, Message.Role.USER, message)

        # Build history
        history = await self._get_history(conversation)

        # Stream response
        start = time.time()
        full_response = ""
        sources = []
        model_used = ""

        await self.send(text_data=json.dumps({
            "type": "stream_start",
            "conversation_id": str(conversation.id),
        }))

        try:
            qdrant_collection = str(conversation.collection_id) if conversation.collection_id else None

            async for event in astream_agent_graph(
                query=message,
                history=history,
                collection_id=qdrant_collection,
                agent_mode=agent_mode,
                user_id=str(self.user.id),
            ):
                if event["type"] == "token":
                    full_response += event["content"]
                    await self.send(text_data=json.dumps({
                        "type": "token",
                        "content": event["content"],
                    }))
                elif event["type"] == "sources":
                    sources = event["sources"]
                elif event["type"] == "metadata":
                    model_used = event.get("model", "")

        except Exception as e:
            logger.exception("Streaming error")
            await self.send_error(f"Agent error: {str(e)[:200]}")
            return

        latency_ms = int((time.time() - start) * 1000)

        # Save assistant message
        await self._save_message(
            conversation,
            Message.Role.ASSISTANT,
            full_response,
            sources=sources,
            model_used=model_used,
            latency_ms=latency_ms,
        )

        await self._increment_usage()

        await self.send(text_data=json.dumps({
            "type": "stream_end",
            "sources": sources,
            "model_used": model_used,
            "latency_ms": latency_ms,
        }))

    async def send_error(self, detail: str):
        await self.send(text_data=json.dumps({"type": "error", "detail": detail}))

    # ---- Database helpers ----

    @database_sync_to_async
    def _check_quota(self) -> bool:
        user = User.objects.get(id=self.user.id)
        return user.has_quota()

    @database_sync_to_async
    def _increment_usage(self):
        user = User.objects.get(id=self.user.id)
        user.increment_usage()

    @database_sync_to_async
    def _get_or_create_conversation(self, message, collection_id, agent_mode):
        if self.conversation_id:
            return Conversation.objects.get(id=self.conversation_id, user=self.user)

        kwargs = {
            "user": self.user,
            "agent_mode": agent_mode,
            "title": message[:100],
        }
        if collection_id:
            kwargs["collection"] = Collection.objects.get(id=collection_id, owner=self.user)
        conv = Conversation.objects.create(**kwargs)
        self.conversation_id = conv.id
        return conv

    @database_sync_to_async
    def _get_history(self, conversation):
        return list(
            conversation.messages.order_by("created_at").values_list("role", "content")
        )

    @database_sync_to_async
    def _save_message(self, conversation, role, content, **kwargs):
        return Message.objects.create(
            conversation=conversation,
            role=role,
            content=content,
            **kwargs,
        )
