"""Custom Pydantic validators."""

from typing import Any
from pydantic import field_validator
from ..config import settings


def validate_email_domain(email: str) -> str:
    """Validate email domain (example: block certain domains)."""
    # Add custom email validation logic here if needed
    return email


def validate_password_strength(password: str) -> str:
    """Validate password strength."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one digit")
    return password

