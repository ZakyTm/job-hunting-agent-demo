# agentic-core/agents/nodes/tailor.py
"""
Tailor Node — Generates a job-specific tailored CV from the master resume.

Input: raw_text, requirements, matched_skills, missing_skills, company_intel, master resume
Output: tailored_cv_md, tailored_cv_path, tailored_cv_diff

RULES (enforced in prompt):
  - NEVER invent experience or skills the candidate doesn't have
  - Only rewrite Professional Summary, reorder Technical Skills, rephrase bullet points
  - Emphasize matched skills, add job-specific keywords from the posting
"""
import os
import json
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

from core.logging import get_logger
from core.llm_client import with_gemini_backoff

log = get_logger(__name__)

load_dotenv()

# ---------------------------------------------------------------------------
# Resume paths
# ---------------------------------------------------------------------------
_RESUME_PATH = Path(__file__).resolve().parent.parent.parent / "resume" / "master_resume.md"
_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "resume" / "output"


def _load_resume() -> str:
    if not _RESUME_PATH.exists():
        raise FileNotFoundError(f"Resume not found at {_RESUME_PATH}")
    return _RESUME_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------
class CVDiff(BaseModel):
    """A single section modification in the CV."""
    section: str = Field(description="Name of the CV section being modified (e.g., 'Professional Summary', 'Technical Skills')")
    original: str = Field(description="The original text of this section (exact match from the CV)")
    replacement: str = Field(description="The tailored replacement text for this section")
    reason: str = Field(description="Why this change was made — what job requirement it addresses")


class TailorResult(BaseModel):
    """Structured output from the Tailor node."""
    diffs: list[CVDiff] = Field(description="List of section-level modifications to apply to the CV")
    summary_of_changes: str = Field(description="Brief summary of what was tailored and why")


# ---------------------------------------------------------------------------
# LLM invocation
# ---------------------------------------------------------------------------
@with_gemini_backoff()
def _invoke_tailor_llm(structured_llm, prompt: str) -> TailorResult:
    return structured_llm.invoke(prompt)


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------
def tailor_node(state) -> dict:
    """
    Generates a tailored CV by prompting Gemini for section-level diffs,
    then applying them to the master resume.
    """
    state_dict = state if isinstance(state, dict) else (state.model_dump() if hasattr(state, "model_dump") else state)

    job_title = state_dict.get("job_title", "Unknown")
    company_name = state_dict.get("company_name", "Unknown")
    requirements = state_dict.get("requirements", [])
    matched_skills = state_dict.get("matched_skills", [])
    missing_skills = state_dict.get("missing_skills", [])
    company_intel = state_dict.get("company_intel") or {}

    resume_text = _load_resume()
    req_text = "\n".join(f"  - {r}" for r in requirements) if requirements else "  (none listed)"
    matched_text = ", ".join(matched_skills) if matched_skills else "N/A"
    missing_text = ", ".join(missing_skills) if missing_skills else "N/A"

    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )
    structured_llm = llm.with_structured_output(TailorResult)

    prompt = f"""You are a professional CV tailoring expert. Your job is to customize the candidate's CV 
for a specific job posting by making targeted, honest modifications.

ABSOLUTE RULES — VIOLATIONS ARE UNACCEPTABLE:
1. NEVER invent experience, projects, skills, or certifications the candidate doesn't have.
2. NEVER change dates, company names, or job titles in the experience section.
3. NEVER add technologies or tools the candidate hasn't used.
4. You may ONLY:
   a. Rewrite the Professional Summary to emphasize relevant experience
   b. Reorder Technical Skills to put the most relevant ones first
   c. Rephrase bullet points to use keywords from the job posting (but keep the same accomplishments)
   d. Slightly adjust emphasis within existing project descriptions

TARGET JOB:
  Title: {job_title}
  Company: {company_name}
  Requirements:
{req_text}

MATCH ANALYSIS:
  Matched Skills: {matched_text}
  Missing Skills: {missing_text}
  Company Talking Point: {company_intel.get("talking_point", "N/A")}

---

CANDIDATE'S CURRENT CV:
{resume_text}

---

Generate a list of section-level diffs to tailor this CV for the target job.
Focus on the Professional Summary and Technical Skills sections.
Only modify sections where the change adds real value.
Keep all modifications honest and verifiable."""

    try:
        result: TailorResult = _invoke_tailor_llm(structured_llm, prompt)

        # Apply diffs to generate the tailored CV
        tailored_cv = resume_text
        diff_list = []
        for diff in result.diffs:
            if diff.original in tailored_cv:
                tailored_cv = tailored_cv.replace(diff.original, diff.replacement, 1)
                diff_list.append({
                    "section": diff.section,
                    "original": diff.original[:100] + "...",
                    "replacement": diff.replacement[:100] + "...",
                    "reason": diff.reason,
                })
            else:
                log.warning("Diff original text not found in CV, skipping", extra={
                    "section": diff.section,
                    "pipeline_step": "tailor",
                })

        # Save to file
        _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        safe_company = "".join(c for c in company_name if c.isalnum() or c in " -_").strip().replace(" ", "_")
        date_str = datetime.now().strftime("%Y%m%d")
        output_filename = f"{safe_company}_{date_str}.md"
        output_path = _OUTPUT_DIR / output_filename
        output_path.write_text(tailored_cv, encoding="utf-8")

        log.info("Tailored CV generated", extra={
            "pipeline_step": "tailor",
            "output_path": str(output_path),
            "num_diffs": len(diff_list),
            "changes_summary": result.summary_of_changes,
        })

        return {
            "tailored_cv_md": tailored_cv,
            "tailored_cv_path": str(output_path),
            "tailored_cv_diff": {
                "diffs": diff_list,
                "summary": result.summary_of_changes,
            },
        }

    except Exception as e:
        log.error("Tailor node failed", extra={"pipeline_step": "tailor"}, exc_info=True)
        return {
            "tailored_cv_md": None,
            "tailored_cv_path": None,
            "tailored_cv_diff": None,
            "error": f"Tailor error: {str(e)}",
        }
