"""Embedding provider implementations."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from django.conf import settings
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    @abstractmethod
    def get_embeddings_model(self) -> Embeddings:
        ...


class AzureOpenAIEmbeddingProvider(EmbeddingProvider):
    def get_embeddings_model(self) -> Embeddings:
        from langchain_openai import AzureOpenAIEmbeddings

        return AzureOpenAIEmbeddings(
            azure_deployment=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )


class BedrockEmbeddingProvider(EmbeddingProvider):
    def get_embeddings_model(self) -> Embeddings:
        from langchain_aws import BedrockEmbeddings

        return BedrockEmbeddings(
            model_id=settings.AWS_BEDROCK_EMBEDDING_MODEL_ID,
            region_name=settings.AWS_BEDROCK_REGION,
        )


EMBEDDING_PROVIDER_MAP: dict[str, type[EmbeddingProvider]] = {
    "azure_openai": AzureOpenAIEmbeddingProvider,
    "bedrock": BedrockEmbeddingProvider,
}
