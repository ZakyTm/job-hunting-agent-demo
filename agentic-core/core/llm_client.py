import time
import os
from functools import wraps
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from langchain_google_genai import ChatGoogleGenerativeAI
from core.logging import get_logger

log = get_logger("llm_client")

def with_gemini_backoff(max_retries: int = 6, base_delay: float = 2.5):
    """Decorator: exponential backoff on Gemini rate limit errors."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return fn(*args, **kwargs)
                except (ResourceExhausted, ServiceUnavailable) as e:
                    wait = base_delay ** attempt
                    log.warning(f"Gemini rate limited or unavailable, retry {attempt+1}/{max_retries} "
                                f"in {wait:.1f}s", extra={"error": str(e)})
                    time.sleep(wait)
                except Exception as e:
                    err_str = str(e)
                    if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str or "quota" in err_str.lower() or "limit" in err_str.lower():
                        wait = base_delay ** attempt
                        log.warning(f"Gemini rate limited (wrapped), retry {attempt+1}/{max_retries} "
                                    f"in {wait:.1f}s", extra={"error": err_str})
                        time.sleep(wait)
                    else:
                        raise e
            raise RuntimeError(f"Gemini failed after {max_retries} retries")
        return wrapper
    return decorator

def get_gemini(temperature: float = 0.1) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=temperature,
        request_timeout=30,
    )
