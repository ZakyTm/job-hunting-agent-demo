# agentic-core/agents/nodes/test_matchmaker.py
"""
Standalone test for the Matchmaker node.
Tests 3 scenarios: perfect match, partial match, and no match.
Run: python agents/nodes/test_matchmaker.py  (from agentic-core/)
"""
import sys
import os

# Add parent dirs to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from agents.nodes.matchmaker import matchmaker_node

# ---------------------------------------------------------------------------
# Test 1: Job you're clearly qualified for (expect 7-9)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("TEST 1: AI Engineer — Strong Match Expected (7-9)")
print("=" * 60)

result_1 = matchmaker_node({
    "job_title": "AI Engineer",
    "company_name": "TechCorp Algeria",
    "requirements": [
        "Python",
        "LangChain or LangGraph experience",
        "Machine Learning fundamentals",
        "FastAPI or Flask",
        "RAG pipeline experience",
        "Git version control",
    ],
    "job_type": "remote",
    "location": "Remote",
})

print(f"  Score: {result_1['match_score']}/10")
print(f"  Reasoning: {result_1['match_reasoning']}")
print(f"  Matched: {result_1['matched_skills']}")
print(f"  Missing: {result_1['missing_skills']}")

# ---------------------------------------------------------------------------
# Test 2: Job you're partially qualified for (expect 4-6)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("TEST 2: DevOps Engineer — Partial Match Expected (4-6)")
print("=" * 60)

result_2 = matchmaker_node({
    "job_title": "DevOps Engineer",
    "company_name": "CloudScale Inc",
    "requirements": [
        "Docker and Kubernetes",
        "CI/CD pipeline management",
        "AWS or GCP certification",
        "Terraform or Ansible",
        "Linux administration",
        "Python scripting",
        "3+ years DevOps experience",
    ],
    "job_type": "onsite",
    "location": "Paris, France",
})

print(f"  Score: {result_2['match_score']}/10")
print(f"  Reasoning: {result_2['match_reasoning']}")
print(f"  Matched: {result_2['matched_skills']}")
print(f"  Missing: {result_2['missing_skills']}")

# ---------------------------------------------------------------------------
# Test 3: Job you're not qualified for (expect 1-3)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("TEST 3: Senior Java Architect — Low Match Expected (1-3)")
print("=" * 60)

result_3 = matchmaker_node({
    "job_title": "Senior Java Architect",
    "company_name": "Enterprise Solutions Ltd",
    "requirements": [
        "10+ years Java development",
        "Spring Boot microservices",
        "Enterprise architecture patterns",
        "Oracle database administration",
        "Team lead experience (5+ engineers)",
        "AWS Solutions Architect certification",
    ],
    "job_type": "onsite",
    "location": "London, UK",
})

print(f"  Score: {result_3['match_score']}/10")
print(f"  Reasoning: {result_3['match_reasoning']}")
print(f"  Matched: {result_3['matched_skills']}")
print(f"  Missing: {result_3['missing_skills']}")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  Test 1 (AI Engineer):         {result_1['match_score']}/10  {'✅' if 7 <= result_1['match_score'] <= 9 else '⚠️'}")
print(f"  Test 2 (DevOps):              {result_2['match_score']}/10  {'✅' if 4 <= result_2['match_score'] <= 6 else '⚠️'}")
print(f"  Test 3 (Senior Java):         {result_3['match_score']}/10  {'✅' if 1 <= result_3['match_score'] <= 3 else '⚠️'}")
