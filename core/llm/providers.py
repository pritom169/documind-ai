"""LLM provider implementations — Azure OpenAI and AWS Bedrock."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import AsyncIterator

from django.conf import settings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def get_chat_model(self, **kwargs) -> BaseChatModel:
        ...

    @abstractmethod
    def get_streaming_model(self, **kwargs) -> BaseChatModel:
        ...


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI provider using langchain-openai."""

    def get_chat_model(self, **kwargs) -> BaseChatModel:
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            temperature=kwargs.get("temperature", 0.1),
            max_tokens=kwargs.get("max_tokens", 4096),
        )

    def get_streaming_model(self, **kwargs) -> BaseChatModel:
        return self.get_chat_model(streaming=True, **kwargs)


class BedrockProvider(LLMProvider):
    """AWS Bedrock provider using langchain-aws."""

    def get_chat_model(self, **kwargs) -> BaseChatModel:
        from langchain_aws import ChatBedrock

        return ChatBedrock(
            model_id=settings.AWS_BEDROCK_MODEL_ID,
            region_name=settings.AWS_BEDROCK_REGION,
            model_kwargs={
                "temperature": kwargs.get("temperature", 0.1),
                "max_tokens": kwargs.get("max_tokens", 4096),
            },
            credentials_profile_name=kwargs.get("profile_name"),
        )

    def get_streaming_model(self, **kwargs) -> BaseChatModel:
        return self.get_chat_model(streaming=True, **kwargs)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

PROVIDER_MAP: dict[str, type[LLMProvider]] = {
    "azure_openai": AzureOpenAIProvider,
    "bedrock": BedrockProvider,
}
