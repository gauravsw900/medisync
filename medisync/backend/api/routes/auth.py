"""
Authentication routes — register, login, token refresh.

Flow:
1. POST /auth/register → creates user + profile, returns tokens
2. POST /auth/login → verifies credentials, returns tokens
3. POST /auth/refresh → exchanges refresh token for new access token
4. GET  /auth/me → returns current user info
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from db.database import get_db
from models.models import User, UserRole, PatientProfile, PhysicianProfile, AuditLog
from schemas.schemas import UserRegister, UserLogin, TokenResponse, RefreshRequest, UserResponse
from core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Register a new user account.

    Creates the base User record plus the appropriate profile
    (PatientProfile or PhysicianProfile) in a single transaction.
    If anything fails, both are rolled back — no orphaned records.
    """
    # Check email is not already registered
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Create the base user
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        role=data.role,
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
    )
    db.add(user)
    await db.flush()  # Get the user ID without committing

    # Create the role-specific profile
    if data.role == UserRole.PATIENT:
        profile = PatientProfile(user_id=user.id)
        db.add(profile)
    elif data.role == UserRole.PHYSICIAN:
        profile = PhysicianProfile(user_id=user.id, specialty="Primary Care")
        db.add(profile)
    # Admin profiles don't need extra data

    # Audit log
    db.add(AuditLog(
        user_id=user.id,
        action="user.registered",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    ))

    await db.commit()
    await db.refresh(user)

    # Generate tokens
    access_token = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Authenticate with email and password, receive JWT tokens.

    We use the same error message for "email not found" and "wrong password"
    to prevent user enumeration attacks (attacker can't tell which is wrong).
    """
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    # Deliberate: same error for wrong email and wrong password
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated — contact your practice administrator",
        )

    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)

    db.add(AuditLog(
        user_id=user.id,
        action="user.login",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    ))

    await db.commit()

    access_token = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """
    Exchange a valid refresh token for a new access token + refresh token pair.
    Rotating refresh tokens on each use limits the window of exposure
    if a refresh token is ever compromised.
    """
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token = create_access_token(str(user.id), user.role.value)
    new_refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's information."""
    return UserResponse.model_validate(current_user)
