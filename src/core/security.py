"""Security utilities for password hashing and verification."""

from passlib.context import CryptContext

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError as e:
        # passlib < 1.7.5 compatibility with bcrypt 4.0+ / strict 3.x
        if "password cannot be longer than 72 bytes" in str(e):
             return False
        raise e


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

