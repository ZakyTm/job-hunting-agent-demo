from pydantic import BaseModel, Field, field_validator
from typing import Optional
import uuid

class JobState(BaseModel):
    """Single source of truth for the entire pipeline. Validated at every node boundary."""
    
    # Identity
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    raw_text: str
    source: str
    source_channel: Optional[str] = None
    source_message_id: Optional[int] = None

    # Scanner outputs
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    contact_email: Optional[str] = None
    requirements: list[str] = Field(default_factory=list)
    job_type: Optional[str] = None
    location: Optional[str] = None

    # Matchmaker outputs
    match_score: Optional[int] = Field(default=None, ge=1, le=10)
    match_reasoning: Optional[str] = None
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)

    # Researcher outputs
    company_intel: Optional[dict] = None

    # Generated outputs (Mini-Plan 05 / 06)
    draft_email: Optional[str] = None
    email_subject: Optional[str] = None
    qa_prep: Optional[str] = None
    tailored_cv_path: Optional[str] = None

    # Pipeline metadata
    status: str = "new"
    error: Optional[str] = None

    @field_validator("requirements", "matched_skills", "missing_skills", mode="before")
    @classmethod
    def coerce_to_list(cls, v):
        """Tolerate comma-separated strings from LLM hallucination."""
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v or []

    @field_validator("match_score", mode="before")
    @classmethod
    def clamp_score(cls, v):
        if v is None:
            return None
        return max(1, min(10, int(v)))
