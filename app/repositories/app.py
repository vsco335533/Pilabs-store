from typing import List, Optional, Any
from sqlalchemy import select, or_, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.app import App, Category, AppVersion
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    def __init__(self):
        super().__init__(Category)

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Optional[Category]:
        query = select(Category).where(
            Category.slug == slug,
            Category.deleted_at.is_(None)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()


class AppRepository(BaseRepository[App]):
    def __init__(self):
        super().__init__(App)

    async def get(self, db: AsyncSession, id: Any) -> Optional[App]:
        query = select(App).where(
            App.id == id,
            App.deleted_at.is_(None)
        ).options(
            selectinload(App.category),
            selectinload(App.versions)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Optional[App]:
        query = select(App).where(
            App.slug == slug,
            App.deleted_at.is_(None)
        ).options(
            selectinload(App.category),
            selectinload(App.versions)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_package_name(self, db: AsyncSession, package_name: str) -> Optional[App]:
        query = select(App).where(
            App.package_name == package_name,
            App.deleted_at.is_(None)
        ).options(
            selectinload(App.category),
            selectinload(App.versions)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def search_apps(
        self,
        db: AsyncSession,
        *,
        query: Optional[str] = None,
        category_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[App]:
        stmt = select(App).where(
            App.is_active == True,
            App.deleted_at.is_(None)
        ).options(
            selectinload(App.category),
            selectinload(App.versions)
        )

        if category_id:
            stmt = stmt.where(App.category_id == category_id)

        if query:
            search_pattern = f"%{query}%"
            stmt = stmt.where(
                or_(
                    App.name.ilike(search_pattern),
                    App.description.ilike(search_pattern),
                    App.developer.ilike(search_pattern)
                )
            )

        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_featured(self, db: AsyncSession, limit: int = 5) -> List[App]:
        # Return latest uploaded or custom flag (here we order by created_at)
        query = select(App).where(
            App.is_active == True,
            App.deleted_at.is_(None)
        ).options(
            selectinload(App.category),
            selectinload(App.versions)
        ).order_by(desc(App.created_at)).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_latest(self, db: AsyncSession, limit: int = 10) -> List[App]:
        query = select(App).where(
            App.is_active == True,
            App.deleted_at.is_(None)
        ).options(
            selectinload(App.category),
            selectinload(App.versions)
        ).order_by(desc(App.created_at)).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())


class AppVersionRepository(BaseRepository[AppVersion]):
    def __init__(self):
        super().__init__(AppVersion)

    async def get_latest_version(self, db: AsyncSession, app_id: str) -> Optional[AppVersion]:
        query = select(AppVersion).where(
            AppVersion.app_id == app_id,
            AppVersion.is_active == True,
            AppVersion.deleted_at.is_(None)
        ).order_by(desc(AppVersion.version_code)).limit(1)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_version_by_code(self, db: AsyncSession, app_id: str, version_code: int) -> Optional[AppVersion]:
        query = select(AppVersion).where(
            AppVersion.app_id == app_id,
            AppVersion.version_code == version_code,
            AppVersion.deleted_at.is_(None)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
