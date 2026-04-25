# agentic-core/agents/job_agent.py
"""
Job Agent — LangGraph StateGraph that wires Scanner → Matchmaker → routing.
This is the brain of the pipeline.
"""
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from agents.nodes.scanner import scanner_node
from agents.nodes.matchmaker import matchmaker_node
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
# Routing function — decides what happens after Matchmaker scores the job
# ---------------------------------------------------------------------------
def route_by_score(state: dict) -> str:
    """
    Route based on match score:
      7+ → high  (future: tailor → ghostwriter → interviewer → saver)
      5-6 → medium (save as "maybe")
      1-4 → low  (save as "ignored")
    """
    score = state.get("match_score", 0)
    if score >= 7:
        return "high"
    elif score >= 5:
        return "medium"
    else:
        return "low"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------
def build_job_agent():
    """Construct and compile the LangGraph StateGraph."""
    graph = StateGraph(JobState)

    # Add nodes
    graph.add_node("scanner", scanner_node)
    graph.add_node("matchmaker", matchmaker_node)
    graph.add_node("saver", saver_node)

    # Set entry point
    graph.set_entry_point("scanner")

    # Scanner always flows to Matchmaker
    graph.add_edge("scanner", "matchmaker")

    # Matchmaker routes based on score
    # For now all routes go to saver. In Mini-Plan 05, "high" will route to "tailor" instead.
    graph.add_conditional_edges("matchmaker", route_by_score, {
        "high":   "saver",    # Future: → tailor → ghostwriter → interviewer → saver
        "medium": "saver",
        "low":    "saver",
    })

    # Saver is the terminal node
    graph.add_edge("saver", END)

    return graph.compile()


# Module-level compiled agent — import and use directly
agent = build_job_agent()
