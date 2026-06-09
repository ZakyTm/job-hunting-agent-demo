# c:\Users\HP\Desktop\JOB-HUNTER-AGENT\01-projects\job-hunting-agent\agentic-core\run_final_test.py
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from agents.job_agent import agent
from core.logging import get_logger

log = get_logger(__name__)

# High match post to guarantee score >= 7 and trigger notification
post = """🚀 We're Hiring — Senior AI Engineer (Remote)

Company: DataFlow Solutions
Location: Remote (worldwide)

We're looking for a talented Senior AI Engineer to join our team.

Requirements:
• 3+ years Python experience
• Extensive experience with LangChain, LangGraph, and RAG pipelines
• FastAPI backend development
• Experience building multi-agent AI systems
• Git, Docker

Apply: careers@dataflow-solutions.com"""

def run():
    print("🚀 Running final high-match E2E pipeline test...")
    result = agent.invoke({
        "raw_text": post,
        "source": "telegram",
        "source_channel": "@TechJobsOccean",
        "source_message_id": 99992
    })
    print("\n=== PIPELINE RESULT ===")
    print(f"Title: {result.get('job_title')}")
    print(f"Company: {result.get('company_name')}")
    print(f"Match Score: {result.get('match_score')}/10")
    print(f"Status: {result.get('status')}")
    print(f"Contact Email: {result.get('contact_email')}")
    print(f"Source Channel: {result.get('source_channel')}")
    print(f"Reasoning: {result.get('match_reasoning')}")
    print("========================")

if __name__ == "__main__":
    run()
