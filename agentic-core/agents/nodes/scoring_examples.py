"""
Ground-truth examples for matchmaker calibration.
These examples help Gemini understand what a "good" vs "bad" match looks like 
for an Applied AI Engineer profile.
"""

CALIBRATION_EXAMPLES = [
    {
        "requirements": [
            "Python", "LangChain", "FastAPI", "RAG", "vector databases",
            "2+ years experience building AI agents", "remote OK"
        ],
        "matched_skills": ["Python", "LangChain", "FastAPI", "RAG", "AI Agents"],
        "missing_skills": ["2+ years experience (I have ~1.5)", "Production vector DB experience"],
        "score": 8,
        "reasoning": "Strong stack overlap. The experience gap is minor for a fast learner with a portfolio. High interview shot."
    },
    {
        "requirements": [
            "Java Spring Boot", "Oracle DB", "5+ years enterprise banking experience", "Onsite Algiers"
        ],
        "matched_skills": [],
        "missing_skills": ["Java", "Spring Boot", "Oracle DB", "5 years experience"],
        "score": 1,
        "reasoning": "Zero overlap with my current focus. Hard requirements are not met."
    },
    {
        "requirements": [
            "Python", "NLP", "Gemini/OpenAI API", "French required", "Remote"
        ],
        "matched_skills": ["Python", "NLP", "LLM APIs", "French"],
        "missing_skills": [],
        "score": 9,
        "reasoning": "Perfect alignment. Language and stack match exactly. Very high match."
    },
    {
        "requirements": [
            "Data Science", "Pandas", "Sklearn", "Tableau", "PhD in Math preferred"
        ],
        "matched_skills": ["Python", "Pandas", "Sklearn"],
        "missing_skills": ["PhD", "Tableau", "Heavy Data Science focus"],
        "score": 4,
        "reasoning": "Relevant skills but the seniority/academic level is a stretch. Low priority."
    }
]
