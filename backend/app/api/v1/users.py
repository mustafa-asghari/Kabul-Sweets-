"""
User management endpoints.
Includes profile management and admin user operations.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, log_admin_action, require_admin
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import (
    MessageResponse,
    PasswordChange,
    UserCreate,
    UserCreateAdmin,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["Users"])
logger = get_logger("users")


# ── Current User Profile ────────────────────────────────────────────────────
@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """Get the current user's profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    updates: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's profile."""
    if updates.full_name is not None:
        current_user.full_name = updates.full_name
    if updates.phone is not None:
        current_user.phone = updates.phone

    await db.flush()
    await db.refresh(current_user)
    logger.info("User updated profile: %s", current_user.email)
    return current_user


@router.post("/me/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the current user's password."""
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = hash_password(password_data.new_password)
    logger.info("User changed password: %s", current_user.email)
    return MessageResponse(message="Password changed successfully")


# ── Admin: User Management ──────────────────────────────────────────────────
@router.get(
    "/",
    response_model=list[UserResponse],
    dependencies=[Depends(require_admin)],
)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    role: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """[Admin] List all users with optional role filter."""
    query = select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
    if role:
        query = query.where(User.role == role)
    result = await db.execute(query)
    return result.scalars().all()


@router.get(
    "/count",
    dependencies=[Depends(require_admin)],
)
async def count_users(
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get total user count."""
    result = await db.execute(select(func.count(User.id)))
    return {"total": result.scalar()}


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_admin)],
)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Get a specific user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_user(
    user_data: UserCreateAdmin,
    admin: User = Depends(log_admin_action),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Create a new user with a specific role."""
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        role=UserRole(user_data.role),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    logger.info("Admin %s created user: %s (role=%s)", admin.email, user.email, user.role.value)
    return user


@router.patch(
    "/{user_id}/deactivate",
    response_model=MessageResponse,
)
async def deactivate_user(
    user_id: uuid.UUID,
    admin: User = Depends(log_admin_action),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Deactivate a user account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    user.is_active = False
    logger.info("Admin %s deactivated user: %s", admin.email, user.email)
    return MessageResponse(message=f"User {user.email} has been deactivated")


@router.patch(
    "/{user_id}/activate",
    response_model=MessageResponse,
)
async def activate_user(
    user_id: uuid.UUID,
    admin: User = Depends(log_admin_action),
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Activate a user account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_active = True
    logger.info("Admin %s activated user: %s", admin.email, user.email)
    return MessageResponse(message=f"User {user.email} has been activated")
