"""LangGraph agent state definitions."""

from __future__ import annotations

from typing import Annotated, Literal

from langchain_core.documents import Document
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """Shared state across all nodes in the agent graph."""

    # Chat messages (LangGraph's built-in message accumulator)
    messages: Annotated[list, add_messages]

    # The user's original query
    query: str

    # Conversation history
    history: list[tuple[str, str]]

    # Which agent mode to use
    agent_mode: Literal["qa", "research", "summarise", "analyse"]

    # Collection ID for RAG retrieval
    collection_id: str | None

    # User ID for personalisation / tracking
    user_id: str

    # Retrieved documents from vector search
    retrieved_documents: list[Document]

    # The generated answer
    answer: str

    # Sources used for the answer
    sources: list[dict]

    # Routing decision
    next_node: str

    # Metadata for observability
    metadata: dict


class RouteDecision(BaseModel):
    """Router output schema — decides which specialist agent handles the query."""

    reasoning: str = Field(description="Brief explanation of the routing decision")
    route: Literal["qa", "research", "summarise", "analyse"] = Field(
        description="The specialist agent to route to"
    )
