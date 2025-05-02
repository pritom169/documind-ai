"""LangGraph agent graph — compiles the multi-agent workflow."""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from .nodes import (
    analyse_agent,
    qa_agent,
    research_agent,
    retrieve_documents,
    route_query,
    summarise_agent,
)
from .state import AgentState

logger = logging.getLogger(__name__)


def _build_graph() -> StateGraph:
    """
    Build the LangGraph agent workflow:

    ┌──────────┐    ┌───────────┐    ┌──────────┐
    │  Router  │───▶│ Retriever │───▶│  Agent   │───▶ END
    └──────────┘    └───────────┘    │ (branch) │
                                     └──────────┘
                                     ┌─ qa_agent
                                     ├─ research_agent
                                     ├─ summarise_agent
                                     └─ analyse_agent
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("router", route_query)
    graph.add_node("retriever", retrieve_documents)
    graph.add_node("qa", qa_agent)
    graph.add_node("research", research_agent)
    graph.add_node("summarise", summarise_agent)
    graph.add_node("analyse", analyse_agent)

    # Entry point
    graph.set_entry_point("router")

    # Router → Retriever
    graph.add_edge("router", "retriever")

    # Retriever → conditional branch to specialist agent
    graph.add_conditional_edges(
        "retriever",
        lambda state: state["next_node"],
        {
            "qa": "qa",
            "research": "research",
            "summarise": "summarise",
            "analyse": "analyse",
        },
    )

    # All agents → END
    graph.add_edge("qa", END)
    graph.add_edge("research", END)
    graph.add_edge("summarise", END)
    graph.add_edge("analyse", END)

    return graph


# Compile the graph once at module level
_compiled_graph = _build_graph().compile()


def run_agent_graph(
    query: str,
    history: list[tuple[str, str]],
    collection_id: str | None,
    agent_mode: str = "qa",
    user_id: str = "",
) -> dict[str, Any]:
    """Run the agent graph synchronously and return the result."""
    initial_state: AgentState = {
        "messages": [HumanMessage(content=query)],
        "query": query,
        "history": history,
        "agent_mode": agent_mode,
        "collection_id": collection_id,
        "user_id": user_id,
        "retrieved_documents": [],
        "answer": "",
        "sources": [],
        "next_node": "",
        "metadata": {},
    }

    result = _compiled_graph.invoke(initial_state)

    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "model": result.get("metadata", {}).get("model", ""),
        "metadata": result.get("metadata", {}),
    }


async def astream_agent_graph(
    query: str,
    history: list[tuple[str, str]],
    collection_id: str | None,
    agent_mode: str = "qa",
    user_id: str = "",
) -> AsyncIterator[dict[str, Any]]:
    """Stream the agent graph execution for WebSocket consumers."""
    from core.llm.factory import LLMFactory

    initial_state: AgentState = {
        "messages": [HumanMessage(content=query)],
        "query": query,
        "history": history,
        "agent_mode": agent_mode,
        "collection_id": collection_id,
        "user_id": user_id,
        "retrieved_documents": [],
        "answer": "",
        "sources": [],
        "next_node": "",
        "metadata": {},
    }

    # Stream through graph nodes
    async for event in _compiled_graph.astream(initial_state, stream_mode="updates"):
        for node_name, node_output in event.items():
            # Emit sources when retriever completes
            if node_name == "retriever" and node_output.get("sources"):
                yield {"type": "sources", "sources": node_output["sources"]}

            # Emit the answer token-by-token
            if node_name in ("qa", "research", "summarise", "analyse"):
                answer = node_output.get("answer", "")
                metadata = node_output.get("metadata", {})

                # Simulate streaming by yielding chunks
                chunk_size = 20
                for i in range(0, len(answer), chunk_size):
                    yield {"type": "token", "content": answer[i : i + chunk_size]}

                yield {"type": "metadata", "model": metadata.get("model", "")}
