# c:\Users\HP\Desktop\JOB-HUNTER-AGENT\01-projects\job-hunting-agent\agentic-core\run_single_job.py
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from agents.job_agent import agent
from core.logging import get_logger

log = get_logger(__name__)

# Highly matching AI Engineer job description that should score >= 7
post = """🚀 We're Hiring — AI Engineer (Remote)

Company: DataFlow Solutions
Location: Remote (worldwide)

We're looking for a talented AI Engineer to join our growing team.

Requirements:
• 2+ years Python experience
• Experience with LangChain, LangGraph, or similar LLM frameworks
• Knowledge of RAG pipelines and vector databases
• FastAPI or Django backend experience
• ML model training and evaluation
• Git, Docker

Nice to have:
• Published research in AI/ML
• Experience with agentic AI patterns

Apply: careers@dataflow-solutions.com"""

def run():
    print("🚀 Running high-match job through the LangGraph pipeline...")
    result = agent.invoke({
        "raw_text": post,
        "source": "telegram",
        "source_channel": "@TechJobsOccean",
        "source_message_id": 9999
    })
    print("\n=== PIPELINE RESULT ===")
    print(f"Title: {result.get('job_title')}")
    print(f"Company: {result.get('company_name')}")
    print(f"Match Score: {result.get('match_score')}/10")
    print(f"Status: {result.get('status')}")
    print(f"Contact Email: {result.get('contact_email')}")
    print(f"Matched Skills: {result.get('matched_skills')}")
    print(f"Missing Skills: {result.get('missing_skills')}")
    print(f"Reasoning: {result.get('match_reasoning')}")
    print(f"Company Intel: {result.get('company_intel')}")
    print("========================")

if __name__ == "__main__":
    run()
