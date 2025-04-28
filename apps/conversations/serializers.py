"""Conversation serializers."""

from rest_framework import serializers

from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            "id",
            "role",
            "content",
            "sources",
            "token_count",
            "latency_ms",
            "model_used",
            "metadata",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "sources",
            "token_count",
            "latency_ms",
            "model_used",
            "metadata",
            "created_at",
        ]


class ConversationSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "collection",
            "title",
            "agent_mode",
            "metadata",
            "is_archived",
            "message_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_message_count(self, obj) -> int:
        return obj.messages.count()


class ConversationDetailSerializer(ConversationSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ["messages"]


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=10000)
    conversation_id = serializers.UUIDField(required=False)
    collection_id = serializers.UUIDField(required=False)
    agent_mode = serializers.ChoiceField(
        choices=["qa", "research", "summarise", "analyse"],
        default="qa",
    )
