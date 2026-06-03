# agentic-core/agents/nodes/ghostwriter.py
"""
Ghostwriter Node — Generates a tailored cover email for a job application.

Input: job_title, company_name, contact_email, requirements, matched_skills, company_intel
Output: draft_email, email_subject

Constraints:
  - Under 200 words
  - 4 paragraphs: Hook, Match, Value, CTA
  - Plain text, professional but not generic
  - Must reference something specific about the company
"""
import os
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

from core.logging import get_logger
from core.llm_client import with_gemini_backoff

log = get_logger(__name__)

load_dotenv()


# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------
class EmailDraft(BaseModel):
    """Structured output from the Ghostwriter node."""
    email_subject: str = Field(description="Email subject line — specific, not generic (e.g., 'Application: AI Engineer — FastAPI + LangGraph Experience')")
    draft_email: str = Field(description="The full email body, 4 paragraphs, under 200 words, plain text")
    word_count: int = Field(description="Word count of the email body")


# ---------------------------------------------------------------------------
# LLM invocation
# ---------------------------------------------------------------------------
@with_gemini_backoff()
def _invoke_ghostwriter_llm(structured_llm, prompt: str) -> EmailDraft:
    return structured_llm.invoke(prompt)


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------
def ghostwriter_node(state) -> dict:
    """
    Generates a tailored application email based on job and candidate data.
    """
    state_dict = state if isinstance(state, dict) else (state.model_dump() if hasattr(state, "model_dump") else state)

    job_title = state_dict.get("job_title", "Unknown Position")
    company_name = state_dict.get("company_name", "Unknown Company")
    contact_email = state_dict.get("contact_email", "N/A")
    requirements = state_dict.get("requirements", [])
    matched_skills = state_dict.get("matched_skills", [])
    missing_skills = state_dict.get("missing_skills", [])
    company_intel = state_dict.get("company_intel") or {}

    req_text = "\n".join(f"  - {r}" for r in requirements) if requirements else "  (none listed)"
    matched_text = ", ".join(matched_skills) if matched_skills else "N/A"
    talking_point = company_intel.get("talking_point", "")
    tech_stack = ", ".join(company_intel.get("tech_stack", [])) if company_intel.get("tech_stack") else "N/A"

    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )
    structured_llm = llm.with_structured_output(EmailDraft)

    prompt = f"""You are a professional email ghostwriter for job applications. 
Write a compelling, specific application email for the candidate.

CANDIDATE PROFILE:
  Name: Zakaria Toumi
  Title: Applied AI Engineer & Full-Stack Developer
  Location: Algeria (open to remote)
  Key Strengths: {matched_text}

TARGET JOB:
  Position: {job_title}
  Company: {company_name}
  Contact: {contact_email}
  Requirements:
{req_text}

COMPANY INTEL:
  Talking Point: {talking_point if talking_point else "N/A"}
  Tech Stack: {tech_stack}

WRITING RULES:
1. EXACTLY 4 paragraphs:
   - Para 1 (HOOK): Open with something specific about the company — a recent project, 
     their mission, or a talking point from the intel. Show you've done your research.
   - Para 2 (MATCH): Highlight 2-3 of the candidate's most relevant skills/experiences 
     that directly match the requirements. Use specific metrics or project names.
   - Para 3 (VALUE): Explain what unique value the candidate would bring to this specific 
     role — not generic "I'm a hard worker" but specific technical impact.
   - Para 4 (CTA): Professional close — express availability for an interview, 
     mention attached CV, thank them.

2. MUST be under 200 words total.
3. Plain text — no markdown, no bullet points, no formatting.
4. Professional but warm — not robotic or overly formal.
5. NEVER use generic phrases like "I am writing to express my interest" or "I am a highly motivated individual".
6. Start with "Dear Hiring Team," (or specific name if we have one).
7. Sign off with the candidate's full name.

Write the email now."""

    try:
        result: EmailDraft = _invoke_ghostwriter_llm(structured_llm, prompt)

        log.info("Draft email generated", extra={
            "pipeline_step": "ghostwriter",
            "job_title": job_title,
            "company": company_name,
            "word_count": result.word_count,
            "subject": result.email_subject,
        })

        return {
            "draft_email": result.draft_email,
            "email_subject": result.email_subject,
        }

    except Exception as e:
        log.error("Ghostwriter node failed", extra={"pipeline_step": "ghostwriter"}, exc_info=True)
        return {
            "draft_email": None,
            "email_subject": None,
            "error": f"Ghostwriter error: {str(e)}",
        }
