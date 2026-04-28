import os
import re
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

from core.logging import get_logger
from core.llm_client import with_gemini_backoff

log = get_logger(__name__)

load_dotenv()


class ScannedJob(BaseModel):
    """Structured output from scanning a raw job post."""
    job_title: str = Field(description="The job title")
    company_name: str = Field(description="The company name")
    contact_email: str | None = Field(default=None, description="Contact email if found")
    requirements: list[str] = Field(description="List of required skills/qualifications")
    job_type: str = Field(description="'remote', 'hybrid', or 'onsite'")
    location: str | None = Field(default=None, description="Job location if mentioned")
    application_url: str | None = Field(default=None, description="Application link if found")


def extract_emails(text: str) -> list[str]:
    """Regex-first email extraction (cheaper than LLM)."""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(pattern, text)


@with_gemini_backoff()
def _invoke_scanner_llm(structured_llm, prompt: str) -> ScannedJob:
    return structured_llm.invoke(prompt)


def scanner_node(state: dict) -> dict:
    """
    Takes raw_text from state, returns structured job data.
    Uses regex for emails first, Gemini for everything else.
    """
    raw_text = state["raw_text"]

    # Step 1: Regex email extraction (fast, free)
    emails = extract_emails(raw_text)

    # Step 2: Gemini structured extraction
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )
    structured_llm = llm.with_structured_output(ScannedJob)

    prompt = f"""Extract job information from this posting.
If the job posting is in Arabic or French, you MUST translate the extracted fields into English.
If you cannot determine a field, use null.
For job_type, infer from context (default to 'onsite' if unclear).
For requirements, list each skill or qualification separately in English.

Job posting:
---
{raw_text}
---"""

    try:
        result: ScannedJob = _invoke_scanner_llm(structured_llm, prompt)
        return {
            "job_title": result.job_title,
            "company_name": result.company_name,
            "contact_email": emails[0] if emails else result.contact_email,
            "requirements": result.requirements,
            "job_type": result.job_type,
            "location": result.location,
            "application_url": result.application_url,
        }
    except Exception as e:
        log.error("Scanner failed", extra={"pipeline_step": "scanner"}, exc_info=True)
        # Return what we can from regex at least
        return {
            "job_title": "PARSE_FAILED",
            "company_name": "UNKNOWN",
            "contact_email": emails[0] if emails else None,
            "requirements": [],
            "job_type": "unknown",
            "location": None,
            "application_url": None,
        }
