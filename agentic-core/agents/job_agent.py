# agentic-core/agents/job_agent.py
"""
Job Agent — LangGraph 0.3 StateGraph with Command-based routing.
Scanner → Matchmaker → (high: Tailor→Ghostwriter→Interviewer | medium/low: Saver)
"""
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from langgraph.types import Command
from agents.nodes.scanner import scanner_node
from agents.nodes.matchmaker import matchmaker_node_v2
from agents.nodes.researcher import researcher_node
from agents.nodes.saver import saver_node

from agents.state import JobState


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------
def build_job_agent():
    """Construct and compile the LangGraph StateGraph."""
    graph = StateGraph(JobState)

    # Add nodes
    graph.add_node("scanner", scanner_node)
    graph.add_node("matchmaker", matchmaker_node_v2) # Returns Command
    graph.add_node("researcher", researcher_node)
    graph.add_node("saver", saver_node)

    # Set entry point
    graph.set_entry_point("scanner")

    # Flow
    graph.add_edge("scanner", "matchmaker")
    # matchmaker_node_v2 uses Command to route dynamically.
    # It routes to "researcher" on high match, or "saver" on low/medium.
    graph.add_edge("researcher", "saver")

    return graph.compile()


# Module-level compiled agent — import and use directly
agent = build_job_agent()
