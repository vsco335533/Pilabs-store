from datetime import datetime, timezone
from typing import List, Optional, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User, RefreshToken, UserSession, OTP, PasswordReset
from app.models.role import Role
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

    async def get(self, db: AsyncSession, id: Any) -> Optional[User]:
        query = select(User).where(
            User.id == id,
            User.deleted_at.is_(None)
        ).options(selectinload(User.role))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        query = select(User).where(
            User.email == email,
            User.deleted_at.is_(None)
        ).options(selectinload(User.role))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_phone_number(self, db: AsyncSession, phone_number: str) -> Optional[User]:
        query = select(User).where(
            User.phone_number == phone_number,
            User.deleted_at.is_(None)
        ).options(selectinload(User.role))
        result = await db.execute(query)
        return result.scalar_one_or_none()


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self):
        super().__init__(RefreshToken)

    async def get_by_token(self, db: AsyncSession, token: str) -> Optional[RefreshToken]:
        query = select(RefreshToken).where(
            RefreshToken.token == token,
            RefreshToken.deleted_at.is_(None)
        ).options(selectinload(RefreshToken.user))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def revoke_user_tokens(self, db: AsyncSession, user_id: str) -> None:
        query = update(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        ).values(is_revoked=True, updated_at=datetime.now(timezone.utc))
        await db.execute(query)


class UserSessionRepository(BaseRepository[UserSession]):
    def __init__(self):
        super().__init__(UserSession)

    async def get_active_sessions(self, db: AsyncSession, user_id: str) -> List[UserSession]:
        query = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.is_active == True,
            UserSession.deleted_at.is_(None)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def deactivate_all_user_sessions(self, db: AsyncSession, user_id: str) -> None:
        query = update(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        ).values(is_active=False, updated_at=datetime.now(timezone.utc))
        await db.execute(query)


class OTPRepository(BaseRepository[OTP]):
    def __init__(self):
        super().__init__(OTP)

    async def get_valid_otp(
        self,
        db: AsyncSession,
        user_id: str,
        code: str,
        otp_type: str
    ) -> Optional[OTP]:
        now = datetime.now(timezone.utc)
        query = select(OTP).where(
            OTP.user_id == user_id,
            OTP.code == code,
            OTP.otp_type == otp_type,
            OTP.is_used == False,
            OTP.expires_at > now,
            OTP.deleted_at.is_(None)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()


class PasswordResetRepository(BaseRepository[PasswordReset]):
    def __init__(self):
        super().__init__(PasswordReset)

    async def get_by_token(self, db: AsyncSession, token: str) -> Optional[PasswordReset]:
        now = datetime.now(timezone.utc)
        query = select(PasswordReset).where(
            PasswordReset.token == token,
            PasswordReset.is_used == False,
            PasswordReset.expires_at > now,
            PasswordReset.deleted_at.is_(None)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
