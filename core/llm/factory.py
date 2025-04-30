"""Factory for creating LLM and embedding instances with caching."""

from __future__ import annotations

import logging
from functools import lru_cache

from django.conf import settings
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from .embeddings import EMBEDDING_PROVIDER_MAP
from .providers import PROVIDER_MAP, LLMProvider

logger = logging.getLogger(__name__)


class LLMFactory:
    """
    Factory that creates LLM / embedding instances based on Django settings.

    Supports provider override per-request so users can choose their
    preferred provider at runtime.
    """

    @staticmethod
    def get_provider(provider_name: str | None = None) -> LLMProvider:
        name = provider_name or settings.LLM_PROVIDER
        cls = PROVIDER_MAP.get(name)
        if cls is None:
            raise ValueError(f"Unknown LLM provider: {name}. Available: {list(PROVIDER_MAP)}")
        return cls()

    @staticmethod
    def get_chat_model(
        provider_name: str | None = None,
        **kwargs,
    ) -> BaseChatModel:
        provider = LLMFactory.get_provider(provider_name)
        return provider.get_chat_model(**kwargs)

    @staticmethod
    def get_streaming_model(
        provider_name: str | None = None,
        **kwargs,
    ) -> BaseChatModel:
        provider = LLMFactory.get_provider(provider_name)
        return provider.get_streaming_model(**kwargs)

    @staticmethod
    def get_embeddings(provider_name: str | None = None) -> Embeddings:
        name = provider_name or settings.LLM_PROVIDER
        cls = EMBEDDING_PROVIDER_MAP.get(name)
        if cls is None:
            raise ValueError(
                f"Unknown embedding provider: {name}. Available: {list(EMBEDDING_PROVIDER_MAP)}"
            )
        return cls().get_embeddings_model()
