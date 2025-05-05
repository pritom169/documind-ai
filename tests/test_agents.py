"""Tests for the LangGraph agent system."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from core.agents.nodes import (
    _format_context,
    qa_agent,
    research_agent,
    route_query,
    retrieve_documents,
)
from core.agents.state import AgentState


def _make_state(**overrides) -> AgentState:
    defaults = {
        "messages": [],
        "query": "What is RAG?",
        "history": [],
        "agent_mode": "qa",
        "collection_id": "test-collection",
        "user_id": "user-1",
        "retrieved_documents": [],
        "answer": "",
        "sources": [],
        "next_node": "",
        "metadata": {},
    }
    defaults.update(overrides)
    return defaults


class TestRouting:
    def test_explicit_mode_skips_llm(self):
        state = _make_state(agent_mode="research")
        result = route_query(state)
        assert result["next_node"] == "research"
        assert result["metadata"]["route_reason"] == "user_selected"

    @patch("core.agents.nodes.LLMFactory")
    def test_router_falls_back_on_parse_error(self, mock_factory):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="not valid json")
        mock_factory.get_chat_model.return_value = mock_llm

        state = _make_state(agent_mode="qa")
        result = route_query(state)
        assert result["next_node"] == "qa"
        assert result["metadata"]["route_reason"] == "fallback"


class TestRetrieval:
    @patch("core.agents.nodes.HybridRetriever")
    def test_retrieve_populates_state(self, mock_retriever_cls):
        docs = [
            Document(
                page_content="Test content",
                metadata={"score": 0.9, "document_id": "d1", "chunk_index": 0},
            )
        ]
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = docs
        mock_retriever_cls.return_value = mock_retriever

        state = _make_state()
        result = retrieve_documents(state)
        assert len(result["retrieved_documents"]) == 1
        assert len(result["sources"]) == 1
        assert result["sources"][0]["score"] == 0.9

    def test_retrieve_no_collection(self):
        state = _make_state(collection_id=None)
        result = retrieve_documents(state)
        assert result["retrieved_documents"] == []


class TestAgentNodes:
    @patch("core.agents.nodes.LLMFactory")
    def test_qa_agent_produces_answer(self, mock_factory):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="RAG combines retrieval with generation.")
        mock_factory.get_chat_model.return_value = mock_llm

        state = _make_state(
            retrieved_documents=[
                Document(page_content="RAG info", metadata={"document_id": "d1"})
            ]
        )
        result = qa_agent(state)
        assert "RAG" in result["answer"]
        assert result["metadata"]["agent"] == "qa"

    @patch("core.agents.nodes.LLMFactory")
    def test_research_agent_produces_answer(self, mock_factory):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Comprehensive analysis of RAG systems.")
        mock_factory.get_chat_model.return_value = mock_llm

        state = _make_state(
            retrieved_documents=[
                Document(page_content="RAG details", metadata={"document_id": "d1"})
            ]
        )
        result = research_agent(state)
        assert len(result["answer"]) > 0
        assert result["metadata"]["agent"] == "research"


class TestHelpers:
    def test_format_context_empty(self):
        assert _format_context([]) == "No documents available."

    def test_format_context_with_docs(self):
        docs = [
            Document(page_content="First doc", metadata={"document_id": "abc12345"}),
            Document(page_content="Second doc", metadata={"document_id": "def67890"}),
        ]
        result = _format_context(docs)
        assert "[Source 1]" in result
        assert "[Source 2]" in result
        assert "First doc" in result
