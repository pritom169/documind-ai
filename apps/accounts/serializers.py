"""Account serializers."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import APIKey

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "password",
            "password_confirm",
            "organisation",
            "preferred_llm_provider",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    usage_percentage = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "organisation",
            "preferred_llm_provider",
            "api_quota_monthly",
            "api_calls_this_month",
            "usage_percentage",
            "created_at",
        ]
        read_only_fields = ["id", "api_quota_monthly", "api_calls_this_month", "created_at"]

    def get_usage_percentage(self, obj) -> float:
        if obj.api_quota_monthly == 0:
            return 0.0
        return round((obj.api_calls_this_month / obj.api_quota_monthly) * 100, 1)


class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = ["id", "name", "prefix", "is_active", "last_used_at", "expires_at", "created_at"]
        read_only_fields = ["id", "prefix", "last_used_at", "created_at"]


class APIKeyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = ["name", "expires_at"]
