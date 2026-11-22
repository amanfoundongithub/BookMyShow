from datetime import datetime
from typing import Literal
from pydantic import BaseModel, EmailStr, Field

UserRole = Literal["USER", "CINEMA", "ADMIN"]


class RegisterRequest(BaseModel):
    """Public registration always creates a standard USER account."""

    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class AdminCreateUserRequest(BaseModel):
    """For admin/seed provisioning of CINEMA or ADMIN accounts."""

    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = "USER"
    cinema_ids: list[str] = Field(default_factory=list)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    user_id: str
    name: str
    email: EmailStr
    role: UserRole = "USER"
    cinema_ids: list[str] = Field(default_factory=list)
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse