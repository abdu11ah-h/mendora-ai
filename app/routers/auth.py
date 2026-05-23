import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from uuid import UUID

from app.database import get_db
from app.models.user import User, EmailVerification, RefreshToken
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshRequest,
    VerifyEmailRequest, ResendVerificationRequest, ForgotPasswordRequest,
    ResetPasswordRequest, UserProfile, UpdateProfileRequest,
)
from app.services.auth_service import (
    get_password_hash, verify_password, create_access_token,
    create_refresh_token, hash_refresh_token, generate_verification_token,
    get_refresh_token_expiry, get_verification_token_expiry,
)
from app.services.email_service import send_verification_email, send_password_reset_email
from app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check duplicate email
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")

    user = User(
        email=data.email,
        password_hash=get_password_hash(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        role=data.role,
        university=data.university,
        department=data.department,
    )
    db.add(user)
    await db.flush()  # get user.id

    # Create verification token
    token = generate_verification_token()
    ev = EmailVerification(
        user_id=user.id,
        token=token,
        token_type="verification",
        expires_at=get_verification_token_expiry(24),
    )
    db.add(ev)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Database error. Ensure PostgreSQL is linked and migrations have run (alembic upgrade head).",
        )

    # Fire-and-forget so SMTP slowness/blocks never hang the HTTP response
    asyncio.create_task(send_verification_email(user.email, token))

    return {"message": "Registered. Please verify your email."}


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(403, "Account is deactivated")
    if not user.is_verified:
        raise HTTPException(403, "Please verify your email first")

    access_token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    raw_refresh, hashed_refresh = create_refresh_token()

    rt = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=get_refresh_token_expiry(),
    )
    db.add(rt)

    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


@router.post("/logout")
async def logout(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    hashed = hash_refresh_token(data.refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hashed))
    rt = result.scalar_one_or_none()
    if rt:
        rt.revoked = True
        await db.commit()
    return {"message": "Logged out"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    hashed = hash_refresh_token(data.refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hashed))
    rt = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if not rt or rt.revoked or rt.expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(401, "Invalid or expired refresh token")

    user_result = await db.execute(select(User).where(User.id == rt.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or deactivated")

    # Rotate refresh token
    rt.revoked = True
    access_token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    raw_refresh, hashed_refresh = create_refresh_token()
    new_rt = RefreshToken(user_id=user.id, token_hash=hashed_refresh, expires_at=get_refresh_token_expiry())
    db.add(new_rt)
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


@router.post("/verify-email")
async def verify_email(data: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EmailVerification).where(
            EmailVerification.token == data.token,
            EmailVerification.token_type == "verification",
            EmailVerification.used == False,
        )
    )
    ev = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if not ev or ev.expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(400, "Invalid or expired verification token")

    ev.used = True
    user_result = await db.execute(select(User).where(User.id == ev.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.is_verified = True
    await db.commit()
    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(data: ResendVerificationRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or user.is_verified:
        # Don't reveal whether email exists
        return {"message": "If the email exists and is unverified, a new email will be sent."}

    token = generate_verification_token()
    ev = EmailVerification(
        user_id=user.id,
        token=token,
        token_type="verification",
        expires_at=get_verification_token_expiry(24),
    )
    db.add(ev)
    await db.commit()
    await send_verification_email(user.email, token)
    return {"message": "Verification email sent"}


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if user:
        token = generate_verification_token()
        ev = EmailVerification(
            user_id=user.id,
            token=token,
            token_type="password_reset",
            expires_at=get_verification_token_expiry(1),
        )
        db.add(ev)
        await db.commit()
        await send_password_reset_email(user.email, token)
    return {"message": "If the email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EmailVerification).where(
            EmailVerification.token == data.token,
            EmailVerification.token_type == "password_reset",
            EmailVerification.used == False,
        )
    )
    ev = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if not ev or ev.expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(400, "Invalid or expired reset token")

    ev.used = True
    user_result = await db.execute(select(User).where(User.id == ev.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.password_hash = get_password_hash(data.new_password)
        # Revoke all refresh tokens
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id)
            .values(revoked=True)
        )
    await db.commit()
    return {"message": "Password reset successfully"}


@router.get("/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserProfile)
async def update_me(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return current_user
