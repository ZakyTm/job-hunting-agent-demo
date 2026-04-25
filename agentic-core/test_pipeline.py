# agentic-core/test_pipeline.py
"""
End-to-end pipeline test.
Sends a raw Telegram job post through: Scanner → Matchmaker → Saver.
Run: python test_pipeline.py  (from agentic-core/)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from agents.job_agent import agent

# ---------------------------------------------------------------------------
# Real-style Telegram job posts for testing
# ---------------------------------------------------------------------------

# Test 1: AI/ML role (should score HIGH — 6+)
test_post_1 = """
🚀 We're Hiring — AI Engineer (Remote)

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

Apply: careers@dataflow-solutions.com
"""

# Test 2: French job post (should score MEDIUM — 4-5)
test_post_2 = """
📢 Offre d'emploi — Développeur Full-Stack

Entreprise: TechAlgérie SARL
Lieu: Alger, Algérie (sur site)

Nous cherchons un développeur Full-Stack expérimenté.

Exigences:
• 5 ans d'expérience minimum en développement web
• Maîtrise de React et Angular
• Node.js et Express
• Base de données MongoDB et PostgreSQL
• Anglais professionnel obligatoire

Envoyez votre CV à: rh@techalgerie.dz
"""

# Test 3: Completely unrelated job (should score LOW — 1-3)
test_post_3 = """
Hiring: Senior Mechanical Engineer

Company: PetroAlgeria
Location: Hassi Messaoud, Algeria (onsite)

We need a Senior Mechanical Engineer for our oil & gas operations.

Requirements:
- 10+ years mechanical engineering experience
- PE license required
- AutoCAD, SolidWorks proficiency
- Oil & gas industry experience mandatory
- Willingness to work in remote desert locations

Contact: hr@petroalgeria.com
"""

# ---------------------------------------------------------------------------
# Run all 3 through the full pipeline
# ---------------------------------------------------------------------------
tests = [
    ("🟢 AI Engineer (Remote)", test_post_1, "@TechJobsOccean"),
    ("🟡 Dev Full-Stack (French)", test_post_2, "@ITR213"),
    ("🔴 Mechanical Engineer", test_post_3, "@rcrdz1"),
]

print("\n" + "=" * 70)
print("  END-TO-END PIPELINE TEST: Scanner → Matchmaker → Saver")
print("=" * 70)

results = []
for label, post, channel in tests:
    print(f"\n{'─'*70}")
    print(f"  INPUT: {label}")
    print(f"  Channel: {channel}")
    print(f"{'─'*70}")

    result = agent.invoke({
        "raw_text": post,
        "source": "telegram",
        "source_channel": channel,
    })
    results.append((label, result))

# ---------------------------------------------------------------------------
# Final summary table
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("  FINAL RESULTS")
print("=" * 70)
for label, r in results:
    score = r.get("match_score", 0)
    status = r.get("status", "unknown")
    title = r.get("job_title", "?")
    company = r.get("company_name", "?")
    email = r.get("contact_email", "N/A")

    if score >= 6:
        emoji = "🟢"
    elif score >= 4:
        emoji = "🟡"
    else:
        emoji = "🔴"

    print(f"  {emoji} {title} @ {company} → {score}/10 [{status}] | Email: {email}")

print("\n✅ Pipeline test complete.")
