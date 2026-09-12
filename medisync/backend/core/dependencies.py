"""
FastAPI dependencies — injected into route handlers via Depends().

The most important one is get_current_user() which:
1. Reads the Authorization header
2. Decodes and validates the JWT
3. Fetches the user from the database
4. Returns the user object (or raises 401)

Role-specific dependencies (get_current_patient, get_current_physician, etc.)
wrap get_current_user() and additionally check the user's role.

Usage in routes:
    @router.get("/my-profile")
    async def get_profile(current_user: User = Depends(get_current_patient)):
        ...
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.database import get_db
from models.models import User, UserRole
from core.security import decode_token

# HTTPBearer extracts the token from "Authorization: Bearer <token>"
bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate JWT and return the current authenticated user.
    Raises 401 if the token is missing, invalid, or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode the JWT
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise credentials_exception

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    # Fetch user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise credentials_exception

    return user


async def get_current_patient(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the current user to be a patient."""
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to patients",
        )
    return current_user


async def get_current_physician(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the current user to be a physician."""
    if current_user.role != UserRole.PHYSICIAN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to physicians",
        )
    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the current user to be an admin."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to administrators",
        )
    return current_user


async def get_physician_or_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Allow physicians and admins (e.g. viewing patient records)."""
    if current_user.role not in [UserRole.PHYSICIAN, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to physicians and administrators",
        )
    return current_user
