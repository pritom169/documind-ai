"""Custom user model with API usage tracking."""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extended user with AI platform-specific fields."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.CharField(max_length=255, blank=True)
    api_quota_monthly = models.PositiveIntegerField(
        default=1000,
        help_text="Max API calls per month",
    )
    api_calls_this_month = models.PositiveIntegerField(default=0)
    preferred_llm_provider = models.CharField(
        max_length=30,
        choices=[("azure_openai", "Azure OpenAI"), ("bedrock", "AWS Bedrock")],
        default="azure_openai",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def has_quota(self) -> bool:
        return self.api_calls_this_month < self.api_quota_monthly

    def increment_usage(self) -> None:
        self.api_calls_this_month = models.F("api_calls_this_month") + 1
        self.save(update_fields=["api_calls_this_month"])


class APIKey(models.Model):
    """User-managed API keys for programmatic access."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys")
    name = models.CharField(max_length=100)
    key_hash = models.CharField(max_length=128, unique=True)
    prefix = models.CharField(max_length=8, help_text="First 8 chars for identification")
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "api_keys"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.prefix}...)"
