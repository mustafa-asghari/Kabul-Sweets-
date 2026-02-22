"""
Authentication endpoints: register, login, refresh, logout, clerk-exchange.
Includes login rate limiting via Redis.
"""

import json
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import jwt as jose_jwt
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
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
from app.models.user import User, UserRole
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
    response: Response,
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

    # Clerk-only users have no hashed_password — reject password login for them
    if user is None or not user.hashed_password or not verify_password(login_data.password, user.hashed_password):
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

    response.headers["Cache-Control"] = "no-store, no-cache, private"
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
    response: Response,
    current_user: User = Depends(get_current_user),
):
    """Get the current authenticated user's profile."""
    # Prevent Cloudflare / any CDN from caching this personal endpoint.
    response.headers["Cache-Control"] = "no-store, no-cache, private, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Vary"] = "Authorization"
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


# ── Clerk Token Exchange ──────────────────────────────────────────────────────

class ClerkExchangeRequest(BaseModel):
    session_token: str


async def _get_clerk_jwks(iss: str) -> dict:
    """Fetch and cache Clerk JWKS for the given issuer (1h TTL)."""
    redis = await get_redis()
    cache_key = f"clerk:jwks:{iss}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    jwks_url = f"{iss}/.well-known/jwks.json"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()
        jwks = resp.json()

    await redis.setex(cache_key, 3600, json.dumps(jwks))
    return jwks


@router.post("/clerk-exchange", response_model=Token)
async def clerk_exchange(
    body: ClerkExchangeRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange a Clerk session token for backend JWT tokens.

    Flow:
    1. Decode Clerk JWT → get issuer (iss)
    2. Fetch JWKS from {iss}/.well-known/jwks.json (cached 1h in Redis)
    3. Verify RS256 signature → extract clerk_user_id (sub)
    4. Fetch full user profile from Clerk API using CLERK_SECRET_KEY
    5. Find existing user by clerk_user_id → email → phone, or create new
    6. Return standard backend access + refresh tokens
    """
    settings = get_settings()
    if not settings.CLERK_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clerk authentication is not configured",
        )

    await check_rate_limit(request, limit=10, window=60)

    # Step 1 — decode without verification to get the issuer claim
    try:
        unverified_claims = jose_jwt.get_unverified_claims(body.session_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Clerk session token",
        )

    iss = unverified_claims.get("iss", "")
    if not iss:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Clerk token: missing issuer",
        )

    # Step 2 — fetch JWKS (Redis-cached)
    try:
        jwks = await _get_clerk_jwks(iss)
    except Exception as exc:
        logger.error("Failed to fetch Clerk JWKS from %s: %s", iss, exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not verify Clerk token (JWKS fetch failed)",
        )

    # Step 3 — verify JWT signature against each key in the JWKS
    verified_claims = None
    for key_data in jwks.get("keys", []):
        try:
            verified_claims = jose_jwt.decode(
                body.session_token,
                key_data,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
            break
        except Exception:
            continue

    if not verified_claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Clerk session token",
        )

    clerk_user_id: str = verified_claims.get("sub", "")
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Clerk token: missing subject",
        )

    # Step 4 — fetch Clerk user profile
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.clerk.com/v1/users/{clerk_user_id}",
                headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
            )
            resp.raise_for_status()
            clerk_profile = resp.json()
    except Exception as exc:
        logger.error("Failed to fetch Clerk user %s: %s", clerk_user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not retrieve Clerk user profile",
        )

    # Extract email
    primary_email_id = clerk_profile.get("primary_email_address_id")
    email: str | None = None
    for addr in clerk_profile.get("email_addresses", []):
        if addr.get("id") == primary_email_id:
            email = addr.get("email_address")
            break
    if email is None:
        addresses = clerk_profile.get("email_addresses", [])
        if addresses:
            email = addresses[0].get("email_address")

    # Extract phone
    phone_numbers = clerk_profile.get("phone_numbers", [])
    phone: str | None = phone_numbers[0].get("phone_number") if phone_numbers else None

    # Extract display name
    first_name = clerk_profile.get("first_name") or ""
    last_name = clerk_profile.get("last_name") or ""
    full_name = (first_name + " " + last_name).strip() or "Customer"

    # Phone-only accounts: use a placeholder email so the DB unique constraint is satisfied
    if not email and phone:
        email = f"{phone}@phone.kabulsweets.internal"
    elif not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No email or phone number found on this Clerk account",
        )

    normalized_email = email.strip().lower()

    # Step 5 — lookup by clerk_user_id → email → phone (link existing accounts)
    # IMPORTANT: never auto-link to an existing account already bound to
    # a different Clerk identity.
    user: User | None = None

    result = await db.execute(select(User).where(User.clerk_user_id == clerk_user_id))
    user = result.scalar_one_or_none()

    if user is None:
        result = await db.execute(
            select(User).where(func.lower(User.email) == normalized_email)
        )
        user = result.scalar_one_or_none()
        if user is not None and user.clerk_user_id and user.clerk_user_id != clerk_user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is linked to another account identity.",
            )

    if user is None and phone:
        # Phone fallback is limited to customer accounts to prevent accidental
        # privilege escalation into staff/admin users.
        result = await db.execute(
            select(User).where(
                User.phone == phone,
                User.role == UserRole.CUSTOMER,
            )
        )
        phone_matches = list(result.scalars().all())
        if len(phone_matches) > 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Multiple customer accounts use this phone number. Contact support.",
            )
        if phone_matches:
            candidate = phone_matches[0]
            if candidate.clerk_user_id and candidate.clerk_user_id != clerk_user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This phone number is linked to another account identity.",
                )
            user = candidate

    if user is not None:
        # Link clerk_user_id on first Clerk sign-in for an existing account
        if not user.clerk_user_id:
            user.clerk_user_id = clerk_user_id
        user.is_verified = True
        user.last_login = datetime.now(timezone.utc)
    else:
        # Create a new Clerk-only user (no password)
        user = User(
            email=normalized_email,
            hashed_password=None,
            full_name=full_name,
            phone=phone,
            clerk_user_id=clerk_user_id,
            is_verified=True,
            role=UserRole.CUSTOMER,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Step 6 — issue backend tokens (same format as the existing login endpoint)
    token_data = {"sub": str(user.id), "role": user.role.value}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    try:
        redis = await get_redis()
        await redis.setex(f"refresh_token:{str(user.id)}", 86400 * 7, refresh_token)
    except Exception as exc:
        logger.warning("Could not store refresh token in Redis: %s", exc)

    response.headers["Cache-Control"] = "no-store, no-cache, private"
    logger.info("Clerk exchange: user %s signed in (clerk_id=%s)", user.email, clerk_user_id)
    return Token(access_token=access_token, refresh_token=refresh_token)
