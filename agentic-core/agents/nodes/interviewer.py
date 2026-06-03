# agentic-core/agents/nodes/interviewer.py
"""
Interviewer Node — Generates interview preparation materials.

Input: job_title, requirements, matched_skills, missing_skills, company_intel
Output: technical_questions, behavioral_questions, questions_to_ask, skill_gap_answers

Generates:
  - 5 technical interview questions (based on requirements)
  - 3 behavioral questions (with STAR format suggestions)
  - 2 questions the candidate should ask the interviewer
  - For each missing_skill: a talking point to address the gap honestly
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
class SkillGapAnswer(BaseModel):
    """How to address a missing skill in an interview."""
    skill: str = Field(description="The missing skill or requirement")
    talking_point: str = Field(description="How to honestly address this gap — transferable skills, learning plan, adjacent experience")


class InterviewPrep(BaseModel):
    """Structured output from the Interviewer node."""
    technical_questions: list[str] = Field(
        description="5 likely technical interview questions based on the job requirements"
    )
    behavioral_questions: list[str] = Field(
        description="3 behavioral interview questions with STAR-format answer hints"
    )
    questions_to_ask: list[str] = Field(
        description="2 smart questions the candidate should ask the interviewer"
    )
    skill_gap_answers: list[SkillGapAnswer] = Field(
        description="For each missing skill, a talking point to address the gap"
    )


# ---------------------------------------------------------------------------
# LLM invocation
# ---------------------------------------------------------------------------
@with_gemini_backoff()
def _invoke_interviewer_llm(structured_llm, prompt: str) -> InterviewPrep:
    return structured_llm.invoke(prompt)


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------
def interviewer_node(state) -> dict:
    """
    Generates comprehensive interview preparation materials.
    """
    state_dict = state if isinstance(state, dict) else (state.model_dump() if hasattr(state, "model_dump") else state)

    job_title = state_dict.get("job_title", "Unknown Position")
    company_name = state_dict.get("company_name", "Unknown Company")
    requirements = state_dict.get("requirements", [])
    matched_skills = state_dict.get("matched_skills", [])
    missing_skills = state_dict.get("missing_skills", [])
    company_intel = state_dict.get("company_intel") or {}

    req_text = "\n".join(f"  - {r}" for r in requirements) if requirements else "  (none listed)"
    matched_text = ", ".join(matched_skills) if matched_skills else "N/A"
    missing_text = "\n".join(f"  - {s}" for s in missing_skills) if missing_skills else "  (none)"
    talking_point = company_intel.get("talking_point", "N/A")
    tech_stack = ", ".join(company_intel.get("tech_stack", [])) if company_intel.get("tech_stack") else "N/A"

    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )
    structured_llm = llm.with_structured_output(InterviewPrep)

    prompt = f"""You are an expert interview coach preparing a candidate for a specific job interview.

CANDIDATE PROFILE:
  Name: Zakaria Toumi
  Background: Applied AI Engineer & Full-Stack Developer, Master's in IT
  Key Strengths: {matched_text}

TARGET JOB:
  Position: {job_title}
  Company: {company_name}
  Requirements:
{req_text}

COMPANY INTEL:
  Talking Point: {talking_point}
  Tech Stack: {tech_stack}

MISSING SKILLS (the candidate LACKS these):
{missing_text}

INSTRUCTIONS:

1. TECHNICAL QUESTIONS (exactly 5):
   - Generate questions the interviewer is LIKELY to ask based on the requirements.
   - Mix difficulty: 2 fundamental, 2 intermediate, 1 advanced.
   - Be specific to the technologies listed (not generic CS questions).
   - Example: "How would you implement a RAG pipeline using LangChain for document Q&A?"

2. BEHAVIORAL QUESTIONS (exactly 3):
   - Standard behavioral questions relevant to this role.
   - For each, include a STAR-format hint suggesting which experience from the candidate's 
     background would make a strong answer.
   - Format: "Question — STAR hint: Use your [specific experience] to answer this."

3. QUESTIONS TO ASK (exactly 2):
   - Smart, specific questions the candidate should ask the interviewer.
   - These should demonstrate knowledge of the company and genuine interest.
   - NOT generic questions like "What does a typical day look like?"

4. SKILL GAP ANSWERS (one per missing skill):
   - For each missing skill, provide an honest talking point.
   - Mention transferable skills, learning plans, or adjacent experience.
   - NEVER tell the candidate to lie or exaggerate.
   - Example: "I haven't worked with Kubernetes directly, but I've containerized 
     applications with Docker and understand orchestration concepts. I'm actively 
     learning K8s through..."

Generate the interview prep now."""

    try:
        result: InterviewPrep = _invoke_interviewer_llm(structured_llm, prompt)

        # Convert SkillGapAnswer objects to dicts for JSON serialization
        gap_answers = [
            {"skill": g.skill, "talking_point": g.talking_point}
            for g in result.skill_gap_answers
        ]

        log.info("Interview prep generated", extra={
            "pipeline_step": "interviewer",
            "job_title": job_title,
            "company": company_name,
            "num_tech_q": len(result.technical_questions),
            "num_behavioral_q": len(result.behavioral_questions),
            "num_gap_answers": len(gap_answers),
        })

        return {
            "technical_questions": result.technical_questions,
            "behavioral_questions": result.behavioral_questions,
            "questions_to_ask": result.questions_to_ask,
            "skill_gap_answers": gap_answers,
        }

    except Exception as e:
        log.error("Interviewer node failed", extra={"pipeline_step": "interviewer"}, exc_info=True)
        return {
            "technical_questions": [],
            "behavioral_questions": [],
            "questions_to_ask": [],
            "skill_gap_answers": [],
            "error": f"Interviewer error: {str(e)}",
        }
