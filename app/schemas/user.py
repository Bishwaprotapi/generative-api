"""
Pydantic schemas for User resource.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    is_superuser: bool = False


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None
    is_active: bool
    is_superuser: bool

    model_config = {"from_attributes": True}
