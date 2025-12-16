"""Rate limiting middleware using slowapi."""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from ..config import settings

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
)

# Rate limit exceeded handler
rate_limit_exceeded_handler = _rate_limit_exceeded_handler


def get_rate_limiter() -> Limiter:
    """Get rate limiter instance."""
    return limiter

