"""
Authentication service.

Contains the business logic for credential verification and token issuance.
The user store here is an in-memory stub — swap for a real DB query in production.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.schemas.auth import MeResponse, TokenResponse

logger = get_logger(__name__)


# ── In-memory user stub (replace with DB layer) ───────────────────────────────

_DEMO_USERS: dict[str, dict] = {
    "admin@example.com": {
        "id": 1,
        "email": "admin@example.com",
        "hashed_password": hash_password("admin123"),
        "is_active": True,
        "is_superuser": True,
    }
}


class AuthService:
    def authenticate(self, email: str, password: str) -> TokenResponse | None:
        """Validate credentials and issue a token pair; returns None on failure."""
        user = _DEMO_USERS.get(email)
        if user is None or not verify_password(password, user["hashed_password"]):
            logger.warning("Failed login attempt for %s", email)
            return None

        access_token = create_access_token(subject=user["id"])
        refresh_token = create_refresh_token(subject=user["id"])
        logger.info("User %s authenticated.", email)
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    def get_current_user(self, user_id: int) -> MeResponse | None:
        """Return user info by numeric ID."""
        for user in _DEMO_USERS.values():
            if user["id"] == user_id:
                return MeResponse(
                    id=user["id"],
                    email=user["email"],
                    is_active=user["is_active"],
                    is_superuser=user["is_superuser"],
                )
        return None


auth_service = AuthService()
