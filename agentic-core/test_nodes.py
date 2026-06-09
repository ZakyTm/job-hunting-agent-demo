"""Quick node-by-node diagnostic to find where the pipeline hangs."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from agents.state import JobState

test_text = "Hiring AI Engineer. Company: TestCo. Location: Remote. Requirements: Python, FastAPI, Docker. Apply: test@testco.com"
state = JobState(raw_text=test_text, source="test")

# 1. Scanner
print("1. Testing Scanner...")
from agents.nodes.scanner import scanner_node
r1 = scanner_node(state)
print(f"   OK: title={r1.get('job_title')}, email={r1.get('contact_email')}")

# 2. Matchmaker
print("2. Testing Matchmaker...")
# Merge scanner output into state
merged = state.model_dump()
merged.update(r1)
state2 = JobState(**merged)
from agents.nodes.matchmaker import matchmaker_node
r2 = matchmaker_node(state2)
print(f"   OK: score={r2.get('match_score')}, status based on score")

# 3. Saver (will try Supabase + Telegram if score >= 7)
print("3. Testing Saver...")
merged.update(r2)
state3 = JobState(**merged)
from agents.nodes.saver import saver_node
r3 = saver_node(state3)
print(f"   OK: status={r3.get('status')}, job_id={r3.get('job_id', 'N/A')}")

print("\nAll nodes passed!")
