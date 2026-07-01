"""
Authentication endpoints: login, logout, token refresh, current-user.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import get_active_user
from app.core.security import decode_access_token
from app.schemas.auth import MeResponse, RefreshRequest, TokenResponse
from app.schemas.common import MessageResponse
from app.services.auth_service import auth_service

router = APIRouter(tags=["Auth"])


@router.post("/auth/login", response_model=TokenResponse, summary="Obtain JWT token pair")
async def login(form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    """Standard OAuth2 password flow — returns access + refresh tokens."""
    tokens = auth_service.authenticate(form.username, form.password)
    if tokens is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return tokens


@router.post("/auth/logout", response_model=MessageResponse, summary="Logout (client-side)")
async def logout() -> MessageResponse:
    """
    JWT logout is stateless — instruct the client to discard its tokens.
    Implement a token blacklist here if revocation is required.
    """
    return MessageResponse(message="Successfully logged out. Discard your tokens.")


@router.post("/auth/refresh", response_model=TokenResponse, summary="Refresh access token")
async def refresh(body: RefreshRequest) -> TokenResponse:
    """Issue a new access token from a valid refresh token."""
    from jose import JWTError

    try:
        payload = decode_access_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    from app.core.security import create_access_token, create_refresh_token

    new_access = create_access_token(subject=int(user_id))
    new_refresh = create_refresh_token(subject=int(user_id))
    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


@router.get("/auth/me", response_model=MeResponse, summary="Current authenticated user")
async def me(current_user: MeResponse = Depends(get_active_user)) -> MeResponse:
    return current_user
