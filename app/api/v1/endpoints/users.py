"""
User CRUD endpoints (template — wire up a real DB session in production).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_active_user, get_superuser
from app.core.security import hash_password
from app.schemas.auth import MeResponse
from app.schemas.common import MessageResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(tags=["Users"])

# ── In-memory store (replace with DB repository) ─────────────────────────────
_users: dict[int, dict] = {}
_next_id = 1


def _get_or_404(user_id: int) -> dict:
    user = _users.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
)
async def create_user(
    body: UserCreate,
    _: MeResponse = Depends(get_superuser),
) -> UserResponse:
    global _next_id
    user = {
        "id": _next_id,
        "email": body.email,
        "hashed_password": hash_password(body.password),
        "full_name": body.full_name,
        "is_active": True,
        "is_superuser": body.is_superuser,
    }
    _users[_next_id] = user
    _next_id += 1
    return UserResponse(**user)


@router.get("/users/{user_id}", response_model=UserResponse, summary="Get user by ID")
async def get_user(
    user_id: int,
    _: MeResponse = Depends(get_active_user),
) -> UserResponse:
    return UserResponse(**_get_or_404(user_id))


@router.put("/users/{user_id}", response_model=UserResponse, summary="Update a user")
async def update_user(
    user_id: int,
    body: UserUpdate,
    _: MeResponse = Depends(get_superuser),
) -> UserResponse:
    user = _get_or_404(user_id)
    updates = body.model_dump(exclude_none=True)
    user.update(updates)
    return UserResponse(**user)


@router.delete("/users/{user_id}", response_model=MessageResponse, summary="Delete a user")
async def delete_user(
    user_id: int,
    _: MeResponse = Depends(get_superuser),
) -> MessageResponse:
    _get_or_404(user_id)
    del _users[user_id]
    return MessageResponse(message=f"User {user_id} deleted.")
