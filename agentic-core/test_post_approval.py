"""Test the post-approval pipeline: Tailor -> Ghostwriter -> Interviewer -> PostSaver."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

JOB_ID = "6dd2b468-6d51-48bf-803d-af68f52cb8af"

print("Testing Post-Approval Pipeline...")
print("Tailor -> Ghostwriter -> Interviewer -> PostSaver")
print("=" * 60)
print(f"Job ID: {JOB_ID}")

from agents.post_approval_agent import run_post_approval_pipeline
result = run_post_approval_pipeline(JOB_ID)

print("\n" + "=" * 60)
print("RESULTS:")
print("=" * 60)

# CV
cv_path = result.get("tailored_cv_path", "N/A")
has_cv = bool(result.get("tailored_cv_md"))
diff_info = result.get("tailored_cv_diff") or {}
print(f"\n--- TAILOR ---")
print(f"  CV saved to: {cv_path}")
print(f"  CV generated: {has_cv}")
print(f"  Changes summary: {diff_info.get('summary', 'N/A')}")

# Email
subj = result.get("email_subject", "N/A")
email = result.get("draft_email", "")
print(f"\n--- GHOSTWRITER ---")
print(f"  Subject: {subj}")
print(f"  Email body:")
if email:
    for line in email.split("\n"):
        print(f"    {line}")
else:
    print("    (no email generated)")

# Interview
tq = result.get("technical_questions", [])
bq = result.get("behavioral_questions", [])
qa = result.get("questions_to_ask", [])
gaps = result.get("skill_gap_answers", [])
print(f"\n--- INTERVIEWER ---")
print(f"  Technical Questions ({len(tq)}):")
for i, q in enumerate(tq, 1):
    print(f"    {i}. {q}")
print(f"  Behavioral Questions ({len(bq)}):")
for i, q in enumerate(bq, 1):
    print(f"    {i}. {q}")
print(f"  Questions to Ask ({len(qa)}):")
for i, q in enumerate(qa, 1):
    print(f"    {i}. {q}")
print(f"  Skill Gap Answers ({len(gaps)}):")
for g in gaps:
    print(f"    - {g.get('skill', '?')}: {g.get('talking_point', '?')[:100]}...")

# Status
status = result.get("status", "?")
print(f"\n--- FINAL STATUS: {status} ---")
print("\nPost-approval pipeline complete!")
