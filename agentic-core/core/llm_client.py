import time
import os
from functools import wraps
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from langchain_google_genai import ChatGoogleGenerativeAI
from core.logging import get_logger

log = get_logger("llm_client")

def with_gemini_backoff(max_retries: int = 4, base_delay: float = 2.0):
    """Decorator: exponential backoff on Gemini rate limit errors."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return fn(*args, **kwargs)
                except ResourceExhausted as e:
                    wait = base_delay ** attempt
                    log.warning(f"Gemini rate limited, retry {attempt+1}/{max_retries} "
                                f"in {wait:.1f}s", extra={"error": str(e)})
                    time.sleep(wait)
                except ServiceUnavailable as e:
                    wait = base_delay ** attempt
                    log.warning(f"Gemini unavailable, retry {attempt+1}/{max_retries}")
                    time.sleep(wait)
            raise RuntimeError(f"Gemini failed after {max_retries} retries")
        return wrapper
    return decorator

def get_gemini(temperature: float = 0.1) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=temperature,
        request_timeout=30,
    )
