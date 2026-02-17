"""
Authentication endpoints: register, login, refresh, logout.
Includes login rate limiting via Redis.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.rate_limiter import check_rate_limit
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.user import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    Token,
    TokenRefresh,
    UserCreate,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger("auth")


# ── Register ─────────────────────────────────────────────────────────────────
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new customer account."""
    normalized_email = user_data.email.strip().lower()

    # Check if email already exists
    result = await db.execute(select(User).where(func.lower(User.email) == normalized_email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Create user
    user = User(
        email=normalized_email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    logger.info("New user registered: %s", user.email)
    return user


# ── Login ────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and return JWT tokens.
    Rate limited to 10 attempts per minute per IP.
    """
    # Rate limit login attempts
    await check_rate_limit(request, limit=10, window=60)

    # Find user
    normalized_email = login_data.email.strip().lower()
    result = await db.execute(select(User).where(func.lower(User.email) == normalized_email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(login_data.password, user.hashed_password):
        # Track failed attempts in Redis
        try:
            redis = await get_redis()
            client_ip = request.client.host if request.client else "unknown"
            fail_key = f"login_fails:{client_ip}"
            await redis.incr(fail_key)
            await redis.expire(fail_key, 900)  # 15 min window
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Update last login
    user.last_login = datetime.now(timezone.utc)

    # Create tokens
    token_data = {"sub": str(user.id), "role": user.role.value}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Store refresh token in Redis for revocation support
    try:
        redis = await get_redis()
        await redis.setex(
            f"refresh_token:{str(user.id)}",
            86400 * 7,  # 7 days
            refresh_token,
        )
    except Exception as e:
        logger.warning("Could not store refresh token in Redis: %s", str(e))

    logger.info("User logged in: %s", user.email)
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


# ── Refresh Token ───────────────────────────────────────────────────────────
@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db),
):
    """Refresh an expired access token using a valid refresh token."""
    payload = decode_token(token_data.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Verify refresh token is still valid in Redis
    try:
        redis = await get_redis()
        stored_token = await redis.get(f"refresh_token:{user_id}")
        if stored_token != token_data.refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Could not verify refresh token in Redis: %s", str(e))

    # Create new tokens
    import uuid
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )

    new_token_data = {"sub": str(user.id), "role": user.role.value}
    new_access = create_access_token(new_token_data)
    new_refresh = create_refresh_token(new_token_data)

    # Update stored refresh token
    try:
        redis = await get_redis()
        await redis.setex(
            f"refresh_token:{str(user.id)}",
            86400 * 7,
            new_refresh,
        )
    except Exception:
        pass

    return Token(access_token=new_access, refresh_token=new_refresh)


# ── Forgot / Reset Password ─────────────────────────────────────────────────
@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a password reset link.
    Always returns the same response to avoid email enumeration.
    """
    generic_message = (
        "If an account exists for this email, a password reset link has been sent."
    )

    normalized_email = payload.email.strip().lower()
    result = await db.execute(select(User).where(func.lower(User.email) == normalized_email))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return MessageResponse(message=generic_message)

    reset_token = create_password_reset_token({"sub": str(user.id)})

    try:
        from app.workers.email_tasks import send_password_reset_email

        send_password_reset_email.delay(
            {
                "customer_email": user.email,
                "customer_name": user.full_name,
                "reset_token": reset_token,
            }
        )
    except Exception as exc:
        logger.warning("Could not enqueue password reset email for %s: %s", user.email, str(exc))

    return MessageResponse(message=generic_message)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using a valid password-reset token."""
    decoded = decode_token(payload.token)
    if decoded is None or decoded.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user_id = decoded.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token payload",
        )

    try:
        parsed_user_id = uuid.UUID(str(user_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token payload",
        )

    result = await db.execute(select(User).where(User.id == parsed_user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user.hashed_password = hash_password(payload.new_password)

    # Revoke active refresh token to force re-authentication after password change.
    try:
        redis = await get_redis()
        await redis.delete(f"refresh_token:{str(user.id)}")
    except Exception as exc:
        logger.warning("Could not revoke refresh token after password reset: %s", str(exc))

    logger.info("Password reset completed for user: %s", user.email)
    return MessageResponse(message="Password has been reset successfully")


# ── Get Current User ────────────────────────────────────────────────────────
@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Get the current authenticated user's profile."""
    return current_user


# ── Logout ───────────────────────────────────────────────────────────────────
@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Logout by revoking the refresh token."""
    try:
        redis = await get_redis()
        await redis.delete(f"refresh_token:{str(current_user.id)}")
    except Exception as e:
        logger.warning("Could not revoke refresh token: %s", str(e))

    logger.info("User logged out: %s", current_user.email)
    return MessageResponse(message="Successfully logged out")
