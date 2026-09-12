"""
Security utilities — JWT token generation/verification and password hashing.

We use:
- bcrypt for password hashing (industry standard, deliberately slow to resist brute force)
- JWT (JSON Web Tokens) for stateless authentication
  - Access token: short-lived (30 min), used for API calls
  - Refresh token: long-lived (7 days), used to get new access tokens
  This pattern avoids forcing users to log in every 30 minutes while
  keeping the blast radius of a leaked access token small.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from core.config import settings

# bcrypt context — automatically handles salting and multiple rounds
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password for storage in the database."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, role: str) -> str:
    """
    Create a short-lived JWT access token.

    Args:
        subject: The user's ID (stored as 'sub' claim)
        role: The user's role (patient/physician/admin)

    Returns:
        Signed JWT string
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(subject),
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """
    Create a long-lived JWT refresh token.
    Refresh tokens only contain the user ID — no role — so even if
    compromised, an attacker can't determine the user's permissions
    without exchanging it for an access token (which we can rate-limit).
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT token.

    Returns:
        The token payload dict, or None if invalid/expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        return None
