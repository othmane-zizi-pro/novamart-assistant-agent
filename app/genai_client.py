"""Shared Gemini client with retry handling.

Free-tier keys enforce low per-minute quotas, so every call that can hit the API
goes through call_with_backoff rather than calling the SDK directly.
"""

import random
import time
from collections.abc import Callable

from google import genai
from google.genai import errors

_client: genai.Client | None = None

RETRYABLE_CODES = {429, 500, 503}


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


def call_with_backoff[T](fn: Callable[[], T], max_attempts: int = 6) -> T:
    delay = 2.0
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except errors.APIError as exc:
            if exc.code not in RETRYABLE_CODES or attempt == max_attempts:
                raise
            time.sleep(delay + random.uniform(0, 1))
            delay = min(delay * 2, 60)
    raise RuntimeError("unreachable")
