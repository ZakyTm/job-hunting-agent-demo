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
from agents.nodes.saver import saver_node

# ---------------------------------------------------------------------------
# State schema — every node reads/writes to this shared dict
# ---------------------------------------------------------------------------
class JobState(TypedDict):
    # --- Input ---
    raw_text: str                       # Original message/job post
    source: str                         # "telegram" or "emplotic"
    source_channel: str                 # Channel name or URL

    # --- After Scanner ---
    job_title: Optional[str]
    company_name: Optional[str]
    contact_email: Optional[str]
    requirements: Optional[list[str]]
    job_type: Optional[str]             # "remote", "hybrid", "onsite"
    location: Optional[str]
    application_url: Optional[str]

    # --- After Matchmaker ---
    match_score: Optional[int]          # 1-10
    match_reasoning: Optional[str]
    matched_skills: Optional[list[str]]
    missing_skills: Optional[list[str]]
    reasoning_trace: Optional[str]      # NEW: Gemini chain-of-thought

    # --- After Tailor (future) ---
    tailored_cv_path: Optional[str]
    cv_changes: Optional[list[str]]

    # --- After Ghostwriter (future) ---
    draft_email: Optional[str]
    email_subject: Optional[str]

    # --- After Interviewer (future) ---
    qa_prep: Optional[str]

    # --- Meta ---
    job_id: Optional[str]
    status: Optional[str]               # "ignored" | "maybe" | "ready" | "sent"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------
def build_job_agent():
    """Construct and compile the LangGraph StateGraph."""
    graph = StateGraph(JobState)

    # Add nodes
    graph.add_node("scanner", scanner_node)
    graph.add_node("matchmaker", matchmaker_node_v2) # Returns Command
    graph.add_node("saver", saver_node)

    # Set entry point
    graph.set_entry_point("scanner")

    # Scanner always flows to Matchmaker
    graph.add_edge("scanner", "matchmaker")

    # Matchmaker now returns Command — no conditional_edges needed!
    # The matchmaker_node_v2 itself decides where to route.

    # Saver is the terminal node
    graph.add_edge("saver", END)

    return graph.compile()


# Module-level compiled agent — import and use directly
agent = build_job_agent()
