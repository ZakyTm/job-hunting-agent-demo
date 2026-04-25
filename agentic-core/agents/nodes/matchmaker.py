# agentic-core/agents/nodes/matchmaker.py
"""
Matchmaker Node — scores a job posting against the user's CV.
Returns a 1-10 match score with reasoning, matched/missing skills.
Uses Gemini 2.5 Flash via LangChain.
"""
import os
from pathlib import Path
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Resume loading — cached at module level so we read the file once, not per call
# ---------------------------------------------------------------------------
_RESUME_PATH = Path(__file__).resolve().parent.parent.parent / "resume" / "master_resume.md"
_resume_cache: str | None = None


def _load_resume() -> str:
    """Load and cache the master resume from disk."""
    global _resume_cache
    if _resume_cache is None:
        if not _RESUME_PATH.exists():
            raise FileNotFoundError(
                f"Resume not found at {_RESUME_PATH}. "
                "Copy your CV to agentic-core/resume/master_resume.md"
            )
        _resume_cache = _RESUME_PATH.read_text(encoding="utf-8")
    return _resume_cache


# ---------------------------------------------------------------------------
# Pydantic schema for structured output
# ---------------------------------------------------------------------------
class MatchResult(BaseModel):
    """Structured output from the Matchmaker node."""
    match_score: int = Field(
        ge=1, le=10,
        description="Overall match score from 1 (no fit) to 10 (perfect fit)"
    )
    match_reasoning: str = Field(
        description="2-3 sentence explanation of why this score was given"
    )
    matched_skills: list[str] = Field(
        description="Skills/qualifications from the job that the candidate HAS"
    )
    missing_skills: list[str] = Field(
        description="Skills/qualifications from the job that the candidate LACKS"
    )


# ---------------------------------------------------------------------------
# The node function — LangGraph compatible
# ---------------------------------------------------------------------------
def matchmaker_node(state: dict) -> dict:
    """
    Compares job requirements against the user's CV.
    Reads from state: job_title, company_name, requirements, job_type, location
    Writes to state: match_score, match_reasoning, matched_skills, missing_skills
    """
    resume_text = _load_resume()

    job_title = state.get("job_title", "Unknown")
    company_name = state.get("company_name", "Unknown")
    requirements = state.get("requirements", [])
    job_type = state.get("job_type", "unknown")
    location = state.get("location", "Not specified")

    # Format requirements as a readable list
    req_text = "\n".join(f"  - {r}" for r in requirements) if requirements else "  (none listed)"

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        model_kwargs={"thought_in_content": True}  # Added based on 25-04-26 research log for reasoning traces
    )
    structured_llm = llm.with_structured_output(MatchResult)

    prompt = f"""You are a strict, honest job-match evaluator. Compare the CANDIDATE's CV against the JOB requirements and score how well they fit.

SCORING RULES (follow these exactly):
- Score 8-10: Candidate meets 80%+ of requirements. Core skills match. Experience level fits.
- Score 6-7: Candidate meets 50-80% of requirements. Has transferable skills. Could realistically get an interview.
- Score 4-5: Candidate meets some requirements but has significant gaps. Worth saving but not a strong match.
- Score 1-3: Candidate is clearly unqualified. Missing most core requirements.

IMPORTANT GUIDELINES:
- Be STRICT. Do not inflate scores to be nice.
- Consider TRANSFERABLE skills (e.g., FastAPI experience counts for "backend development").
- Penalize hard requirements the candidate clearly lacks (e.g., "10 years Java" when they have 0).
- If the job requires a specific location and the candidate is in Algeria, factor that in realistically.
- For remote jobs, location should not penalize the score.
- "{job_type}" is the job type — weight location requirements accordingly.

---

JOB POSTING:
  Title: {job_title}
  Company: {company_name}
  Type: {job_type}
  Location: {location}
  Requirements:
{req_text}

---

CANDIDATE CV:
{resume_text}

---

Evaluate the match. Be honest and specific in your reasoning."""

    try:
        result: MatchResult = structured_llm.invoke(prompt)
        return {
            "match_score": result.match_score,
            "match_reasoning": result.match_reasoning,
            "matched_skills": result.matched_skills,
            "missing_skills": result.missing_skills,
        }
    except Exception as e:
        print(f"⚠️ Matchmaker failed: {e}")
        return {
            "match_score": 0,
            "match_reasoning": f"Matchmaker error: {str(e)}",
            "matched_skills": [],
            "missing_skills": [],
        }
