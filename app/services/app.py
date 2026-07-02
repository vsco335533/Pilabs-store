import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.custom_exceptions import NotFoundException
from app.models.app import App, Category
from app.repositories import app_repo, category_repo, app_version_repo, download_repo
from app.schemas.app import AppResponse, AppDetailResponse, CategoryResponse


class AppService:
    async def list_categories(self, db: AsyncSession) -> List[CategoryResponse]:
        categories = await category_repo.get_multi(db)
        return [CategoryResponse.model_validate(c) for c in categories]

    async def list_apps(
        self,
        db: AsyncSession,
        *,
        query: Optional[str] = None,
        category_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AppResponse]:
        apps = await app_repo.search_apps(
            db,
            query=query,
            category_id=category_id,
            skip=skip,
            limit=limit
        )

        response_list = []
        for app in apps:
            await db.refresh(app, ["category", "versions"])
            latest_ver = await app_version_repo.get_latest_version(db, app.id)
            app_res = AppResponse.model_validate(app)
            app_res.latest_version = latest_ver
            response_list.append(app_res)

        return response_list

    async def get_app_details(self, db: AsyncSession, id_or_slug: str, user_id: Optional[uuid.UUID] = None) -> AppDetailResponse:
        # Check if UUID
        app = None
        try:
            app_uuid = uuid.UUID(id_or_slug)
            app = await app_repo.get(db, app_uuid)
        except ValueError:
            app = await app_repo.get_by_slug(db, id_or_slug)

        if not app or not app.is_active:
            raise NotFoundException("Application not found or disabled")

        # Explicitly load category and versions asynchronously to prevent MissingGreenlet errors
        await db.refresh(app, ["category", "versions"])

        # Get latest version
        latest_ver = await app_version_repo.get_latest_version(db, app.id)
        downloads_count = await download_repo.get_download_count(db, app.id)

        app_res = AppDetailResponse.model_validate(app)
        app_res.latest_version = latest_ver
        app_res.downloads_count = downloads_count
        app_res.versions = app.versions

        return app_res

    async def get_featured(self, db: AsyncSession, limit: int = 5) -> List[AppResponse]:
        apps = await app_repo.get_featured(db, limit=limit)
        response_list = []
        for app in apps:
            await db.refresh(app, ["category", "versions"])
            latest_ver = await app_version_repo.get_latest_version(db, app.id)
            app_res = AppResponse.model_validate(app)
            app_res.latest_version = latest_ver
            response_list.append(app_res)
        return response_list

    async def get_latest(self, db: AsyncSession, limit: int = 10) -> List[AppResponse]:
        apps = await app_repo.get_latest(db, limit=limit)
        response_list = []
        for app in apps:
            await db.refresh(app, ["category", "versions"])
            latest_ver = await app_version_repo.get_latest_version(db, app.id)
            app_res = AppResponse.model_validate(app)
            app_res.latest_version = latest_ver
            response_list.append(app_res)
        return response_list
