"""
FastAPI dependency providers.

Centralises all dependency-injection callables used in route handlers.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app.core.security import decode_access_token
from app.schemas.auth import MeResponse
from app.services.auth_service import auth_service
from app.services.cache_service import cache_service
from app.services.file_service import file_service
from app.services.llm_service import llm_service
from app.services.prompt_service import prompt_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── LLM / Prompt / Cache / File service deps ─────────────────────────────────


def get_llm_service():
    return llm_service


def get_prompt_service():
    return prompt_service


def get_cache_service():
    return cache_service


def get_file_service():
    return file_service


# ── Auth dependencies ─────────────────────────────────────────────────────────


async def get_current_user(token: str = Depends(oauth2_scheme)) -> MeResponse:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user = auth_service.get_current_user(int(user_id))
    if user is None:
        raise credentials_exc
    return user


async def get_active_user(current_user: MeResponse = Depends(get_current_user)) -> MeResponse:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


async def get_superuser(current_user: MeResponse = Depends(get_active_user)) -> MeResponse:
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")
    return current_user
