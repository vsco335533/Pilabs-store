from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import Role, Permission
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    def __init__(self):
        super().__init__(Role)

    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[Role]:
        query = select(Role).where(
            Role.name == name,
            Role.deleted_at.is_(None)
        ).options(selectinload(Role.permissions))
        result = await db.execute(query)
        return result.scalar_one_or_none()


class PermissionRepository(BaseRepository[Permission]):
    def __init__(self):
        super().__init__(Permission)

    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[Permission]:
        query = select(Permission).where(
            Permission.name == name,
            Permission.deleted_at.is_(None)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
