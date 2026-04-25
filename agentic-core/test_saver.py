import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from agents.nodes.saver import saver_node

mock_state = {
    "raw_text": "Mock job text",
    "source": "telegram",
    "source_channel": "@test",
    "job_title": "Test AI Engineer",
    "company_name": "Test Company",
    "contact_email": "test@example.com",
    "requirements": ["Python", "Machine Learning"],
    "match_score": 8,
    "match_reasoning": "Great fit",
    "matched_skills": ["Python"],
    "missing_skills": [],
}

print("Running saver_node with mock state...")
result = saver_node(mock_state)
print("Finished!")
