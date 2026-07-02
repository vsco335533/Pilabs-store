from typing import Optional
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_db
from app.exceptions.custom_exceptions import AuthenticationException, AuthorizationException
from app.models.user import User
from app.repositories import user_repo
from app.security.security import verify_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    token = credentials.credentials
    payload = verify_token(token, settings.SECRET_KEY)
    if not payload:
        raise AuthenticationException("Could not validate credentials")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationException("Invalid token payload")

    user = await user_repo.get(db, user_id)
    if not user:
        raise AuthenticationException("User not found")

    await db.refresh(user, ["role"])

    if not user.is_active:
        raise AuthenticationException("User account is disabled")

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_verified:
        raise AuthorizationException("Email not verified")
    return current_user


class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.name not in self.allowed_roles:
            raise AuthorizationException(
                f"Role '{current_user.role.name}' does not have permission to access this resource"
            )
        return current_user


# Role-based dependency singletons
require_admin = RoleChecker(["Admin", "Super Admin"])
require_superadmin = RoleChecker(["Super Admin"])
