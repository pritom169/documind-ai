"""LangGraph node functions — each node represents a step in the agent pipeline."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

from core.llm.factory import LLMFactory
from core.rag.retriever import HybridRetriever

from .state import AgentState, RouteDecision

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Router node
# ---------------------------------------------------------------------------

ROUTER_PROMPT = """You are a query router for a document intelligence platform.
Analyse the user's query and decide which specialist agent should handle it.

Available agents:
- qa: Direct question answering from documents. Best for factual questions.
- research: Deep research across multiple documents. Best for complex, multi-faceted questions.
- summarise: Document or section summarisation. Best when user wants overviews or summaries.
- analyse: Data analysis and comparison. Best for analytical questions comparing information.

The user has selected mode: {agent_mode}

Respond with the routing decision."""


def route_query(state: AgentState) -> AgentState:
    """Decide which specialist agent should handle the query."""
    # If user explicitly chose a mode, respect it
    if state.get("agent_mode") and state["agent_mode"] != "qa":
        state["next_node"] = state["agent_mode"]
        state["metadata"] = {**state.get("metadata", {}), "route_reason": "user_selected"}
        return state

    llm = LLMFactory.get_chat_model(temperature=0)
    parser = PydanticOutputParser(pydantic_object=RouteDecision)

    messages = [
        SystemMessage(content=ROUTER_PROMPT.format(agent_mode=state.get("agent_mode", "qa"))),
        HumanMessage(content=f"Query: {state['query']}\n\n{parser.get_format_instructions()}"),
    ]

    response = llm.invoke(messages)
    try:
        decision = parser.parse(response.content)
        state["next_node"] = decision.route
        state["metadata"] = {
            **state.get("metadata", {}),
            "route_reason": decision.reasoning,
        }
    except Exception:
        state["next_node"] = "qa"
        state["metadata"] = {**state.get("metadata", {}), "route_reason": "fallback"}

    logger.info("Routed query to: %s", state["next_node"])
    return state


# ---------------------------------------------------------------------------
# Retrieval node
# ---------------------------------------------------------------------------


def retrieve_documents(state: AgentState) -> AgentState:
    """Retrieve relevant documents from the vector store."""
    collection_id = state.get("collection_id")
    if not collection_id:
        state["retrieved_documents"] = []
        return state

    retriever = HybridRetriever(
        collection_id=collection_id,
        top_k=10,
        rerank_top_k=5,
        use_compression=False,
    )
    docs = retriever.retrieve(state["query"])
    state["retrieved_documents"] = docs

    state["sources"] = [
        {
            "content": doc.page_content[:300],
            "score": doc.metadata.get("score", 0),
            "document_id": doc.metadata.get("document_id", ""),
            "chunk_index": doc.metadata.get("chunk_index", 0),
        }
        for doc in docs
    ]

    logger.info("Retrieved %d documents", len(docs))
    return state


# ---------------------------------------------------------------------------
# Specialist agent nodes
# ---------------------------------------------------------------------------

QA_SYSTEM_PROMPT = """You are a precise question-answering assistant.
Answer the user's question based ONLY on the provided context.
If the context doesn't contain the answer, say so clearly.
Cite specific sources using [Source N] notation.

Context:
{context}"""


def qa_agent(state: AgentState) -> AgentState:
    """Direct Q&A from retrieved documents."""
    context = _format_context(state["retrieved_documents"])
    llm = LLMFactory.get_chat_model(temperature=0.1)

    messages = _build_messages(QA_SYSTEM_PROMPT.format(context=context), state)
    response = llm.invoke(messages)

    state["answer"] = response.content
    state["metadata"] = {
        **state.get("metadata", {}),
        "agent": "qa",
        "model": getattr(llm, "model_name", str(type(llm).__name__)),
    }
    return state


RESEARCH_SYSTEM_PROMPT = """You are a thorough research analyst.
Synthesise information from multiple sources to provide comprehensive analysis.
Structure your response with clear sections and cite sources using [Source N].
Identify patterns, contradictions, and gaps in the available information.

Context:
{context}"""


def research_agent(state: AgentState) -> AgentState:
    """Deep research across multiple documents."""
    context = _format_context(state["retrieved_documents"])
    llm = LLMFactory.get_chat_model(temperature=0.2, max_tokens=8192)

    messages = _build_messages(RESEARCH_SYSTEM_PROMPT.format(context=context), state)
    response = llm.invoke(messages)

    state["answer"] = response.content
    state["metadata"] = {
        **state.get("metadata", {}),
        "agent": "research",
        "model": getattr(llm, "model_name", str(type(llm).__name__)),
    }
    return state


SUMMARISE_SYSTEM_PROMPT = """You are an expert summariser.
Provide a clear, well-structured summary of the provided documents.
Use bullet points for key findings and maintain the original meaning.
Include section headers for different topics.

Context:
{context}"""


def summarise_agent(state: AgentState) -> AgentState:
    """Summarise documents or sections."""
    context = _format_context(state["retrieved_documents"])
    llm = LLMFactory.get_chat_model(temperature=0.1, max_tokens=4096)

    messages = _build_messages(SUMMARISE_SYSTEM_PROMPT.format(context=context), state)
    response = llm.invoke(messages)

    state["answer"] = response.content
    state["metadata"] = {
        **state.get("metadata", {}),
        "agent": "summarise",
        "model": getattr(llm, "model_name", str(type(llm).__name__)),
    }
    return state


ANALYSE_SYSTEM_PROMPT = """You are a data analyst specialising in document analysis.
Compare, contrast, and extract insights from the provided documents.
Use structured formats (tables, lists) when comparing information.
Highlight trends, anomalies, and actionable insights.

Context:
{context}"""


def analyse_agent(state: AgentState) -> AgentState:
    """Analytical comparison across documents."""
    context = _format_context(state["retrieved_documents"])
    llm = LLMFactory.get_chat_model(temperature=0.1, max_tokens=8192)

    messages = _build_messages(ANALYSE_SYSTEM_PROMPT.format(context=context), state)
    response = llm.invoke(messages)

    state["answer"] = response.content
    state["metadata"] = {
        **state.get("metadata", {}),
        "agent": "analyse",
        "model": getattr(llm, "model_name", str(type(llm).__name__)),
    }
    return state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_context(documents) -> str:
    if not documents:
        return "No documents available."

    parts = []
    for i, doc in enumerate(documents, 1):
        source_id = doc.metadata.get("document_id", "unknown")[:8]
        parts.append(f"[Source {i}] (doc: {source_id})\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def _build_messages(system_prompt: str, state: AgentState) -> list:
    messages = [SystemMessage(content=system_prompt)]

    # Add conversation history
    for role, content in state.get("history", [])[-10:]:
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=state["query"]))
    return messages
