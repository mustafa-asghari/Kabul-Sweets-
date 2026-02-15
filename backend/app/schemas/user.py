"""
Pydantic schemas for user operations and authentication.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ── Registration ─────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    """Schema for creating a new user."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: str | None = Field(None, max_length=20)


class UserCreateAdmin(UserCreate):
    """Schema for admin-created users (can set role)."""
    role: str = "customer"


# ── Login ────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    """Schema for login requests."""
    email: EmailStr
    password: str


# ── Tokens ───────────────────────────────────────────────────────────────────
class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Refresh token request."""
    refresh_token: str


# ── User Responses ───────────────────────────────────────────────────────────
class UserResponse(BaseModel):
    """Public user response (safe to return to client)."""
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: datetime | None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    full_name: str | None = Field(None, min_length=1, max_length=255)
    phone: str | None = Field(None, max_length=20)


class PasswordChange(BaseModel):
    """Schema for password change."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


# ── Generic Responses ────────────────────────────────────────────────────────
class MessageResponse(BaseModel):
    """Simple message response."""
    message: str
    detail: str | None = None
