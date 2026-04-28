import os
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from core.logging import get_logger
from core.llm_client import with_gemini_backoff

log = get_logger(__name__)

load_dotenv()

class CompanyIntel(BaseModel):
    """Structured research about the hiring company."""
    company_size: str | None = Field(description="Startup, SME, or Enterprise")
    tech_stack: list[str] = Field(description="Key technologies or frameworks they use")
    recent_news: str | None = Field(description="Recent funding, product launches, or news")
    talking_point: str = Field(description="A specific insight to mention in a cover letter")

def _invoke_researcher_llm(structured_llm, prompt: str) -> CompanyIntel:
    return structured_llm.invoke(prompt)

_invoke_researcher_llm = with_gemini_backoff()(_invoke_researcher_llm)

def researcher_node(state: dict) -> dict:
    """
    Enriches the job data with company research using Gemini.
    Only runs if the match score is decent (>= 5).
    """
    score = state.get("match_score", 0)
    company = state.get("company_name", "Unknown")
    
    if score < 5 or company == "Unknown":
        return {"company_intel": None}

    log.info("Researching company", extra={"company": company, "pipeline_step": "researcher", "job_id": state.get("job_id")})

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )
    
    # We use a structured output to get clean data
    structured_llm = llm.with_structured_output(CompanyIntel)

    prompt = f"""Research the company '{company}' for a job applicant.
Role: {state.get('job_title')}
Location: {state.get('location')}

Find their primary tech stack, company size, and any major news from the last 6 months.
Identify ONE high-value talking point the applicant can use to show they've done their research.
If you can't find specific info, use your internal knowledge to provide a highly likely profile.
"""

    try:
        intel = _invoke_researcher_llm(structured_llm, prompt)
        return {"company_intel": intel.dict()}
    except Exception as e:
        log.error("Research failed", extra={"company": company, "pipeline_step": "researcher", "job_id": state.get("job_id")}, exc_info=True)
        return {"company_intel": None}
