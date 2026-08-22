"""
CleanTrack AI — Auth Service
Handles registration, login, token refresh, logout.
"""
import uuid
from datetime import datetime, timezone
from typing import Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import CleanTrackException
from app.core.redis_client import (
    revoke_refresh_token, store_refresh_token, validate_refresh_token
)
from app.core.security import (
    create_access_token, create_refresh_token,
    decode_token, hash_password, verify_password
)
from app.models.user import User, UserRole
from app.schemas.auth import UserRegisterRequest, UserLoginRequest, TokenResponse

settings = get_settings()


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, data: UserRegisterRequest) -> User:
        # Check duplicate email
        result = await self.db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            raise CleanTrackException("Email already registered", status_code=409)

        user = User(
            email=data.email,
            phone=data.phone,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            role=data.role,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def login(self, data: UserLoginRequest) -> Tuple[User, TokenResponse]:
        result = await self.db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.hashed_password):
            raise CleanTrackException("Invalid email or password", status_code=401)
        if not user.is_active:
            raise CleanTrackException("Account is deactivated", status_code=403)

        # Update device tokens and last login
        if data.fcm_token:
            user.fcm_token = data.fcm_token
        if data.apns_token:
            user.apns_token = data.apns_token
        user.last_login_at = datetime.now(timezone.utc)

        access_token = create_access_token(user.id, user.role)
        refresh_token = create_refresh_token(user.id)

        ttl = settings.refresh_token_expire_days * 86400
        await store_refresh_token(str(user.id), refresh_token, ttl)

        return user, TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise CleanTrackException("Invalid refresh token", status_code=401)

        user_id = payload["sub"]
        is_valid = await validate_refresh_token(user_id, refresh_token)
        if not is_valid:
            raise CleanTrackException("Refresh token revoked or expired", status_code=401)

        result = await self.db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise CleanTrackException("User not found", status_code=401)

        new_access = create_access_token(user.id, user.role)
        new_refresh = create_refresh_token(user.id)
        ttl = settings.refresh_token_expire_days * 86400
        await store_refresh_token(user_id, new_refresh, ttl)

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def logout(self, user_id: str) -> None:
        await revoke_refresh_token(user_id)
