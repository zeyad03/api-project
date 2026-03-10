"""Rate limiting configuration for the F1 Facts API.

Uses slowapi (built on top of the ``limits`` library) to enforce
per-IP request rate limits.  The *limiter* instance is imported by
``main.py`` (to attach middleware / state) and optionally by
individual routers that need stricter per-endpoint limits.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from src.config.settings import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri="memory://",
)
