from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from typing import Dict, Any, List
from slugify import slugify
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions.custom_exceptions import ConflictException, NotFoundException, ValidationException
from app.models.app import App, Category, AppVersion
from app.models.user import User, UserSession
from app.models.log import Download, AuditLog
from app.repositories import (
    app_repo,
    category_repo,
    app_version_repo,
    user_repo,
    download_repo,
    user_session_repo,
    audit_log_repo
)
from app.schemas.app import AppCreate, AppUpdate, AppVersionCreate, CategoryCreate
from app.schemas.admin import DashboardAnalyticsResponse, SystemStatsResponse, DownloadStatItem, CategoryDownloadStat


class AdminService:
    async def create_category(self, db: AsyncSession, data: CategoryCreate, admin_id: UUID) -> Category:
        slug = slugify(data.name)
        existing = await category_repo.get_by_slug(db, slug)
        if existing:
            raise ConflictException("Category already exists")

        cat_in = {
            "name": data.name,
            "slug": slug,
            "description": data.description
        }
        category = await category_repo.create(db, obj_in=cat_in, created_by=admin_id)
        await db.commit()
        await db.refresh(category)

        # Audit Log
        await audit_log_repo.create(
            db,
            obj_in={
                "user_id": admin_id,
                "action": "create_category",
                "resource": "categories",
                "new_values": {"name": category.name, "slug": category.slug}
            }
        )
        await db.commit()

        return category

    async def create_app(self, db: AsyncSession, data: AppCreate, admin_id: UUID) -> App:
        # Check package name (including soft-deleted ones)
        pkg_query = select(App).where(App.package_name == data.package_name)
        pkg_result = await db.execute(pkg_query)
        existing_app = pkg_result.scalar_one_or_none()

        if existing_app:
            if existing_app.deleted_at is None:
                raise ConflictException("An application with this package name already exists")
            
            # Reactivate and update the soft-deleted app
            existing_app.deleted_at = None
            existing_app.is_active = True
            existing_app.name = data.name
            existing_app.developer = data.developer
            existing_app.description = data.description
            existing_app.logo_url = data.logo_url
            existing_app.screenshots = data.screenshots or []
            existing_app.category_id = data.category_id
            existing_app.updated_by = admin_id
            
            db.add(existing_app)
            await db.commit()
            await db.refresh(existing_app, ["category", "versions"])
            
            # Audit
            await audit_log_repo.create(
                db,
                obj_in={
                    "user_id": admin_id,
                    "action": "restore_app",
                    "resource": "apps",
                    "new_values": {"name": existing_app.name, "package_name": existing_app.package_name}
                }
            )
            await db.commit()
            return existing_app

        # Validate category
        category = await category_repo.get(db, data.category_id)
        if not category:
            raise NotFoundException("Category not found")

        slug = slugify(data.name)
        # Check slug conflicts (including soft-deleted ones)
        slug_query = select(App).where(App.slug == slug)
        slug_result = await db.execute(slug_query)
        if slug_result.scalar_one_or_none():
            slug = f"{slug}-{str(uuid4())[:8]}"

        app_in = {
            "name": data.name,
            "slug": slug,
            "package_name": data.package_name,
            "developer": data.developer,
            "description": data.description,
            "logo_url": data.logo_url,
            "screenshots": data.screenshots or [],
            "category_id": data.category_id,
            "is_active": True
        }
        app = await app_repo.create(db, obj_in=app_in, created_by=admin_id)
        await db.commit()
        await db.refresh(app, ["category", "versions"])

        # Audit
        await audit_log_repo.create(
            db,
            obj_in={
                "user_id": admin_id,
                "action": "create_app",
                "resource": "apps",
                "new_values": {"name": app.name, "package_name": app.package_name}
            }
        )
        await db.commit()

        return app

    async def update_app(self, db: AsyncSession, app_id: UUID, data: AppUpdate, admin_id: UUID) -> App:
        app = await app_repo.get(db, app_id)
        if not app:
            raise NotFoundException("Application not found")

        old_values = {
            "name": app.name,
            "package_name": app.package_name,
            "developer": app.developer,
            "is_active": app.is_active,
            "category_id": str(app.category_id)
        }

        updated = await app_repo.update(db, db_obj=app, obj_in=data, updated_by=admin_id)
        await db.commit()
        await db.refresh(updated, ["category", "versions"])

        new_values = {
            "name": updated.name,
            "package_name": updated.package_name,
            "developer": updated.developer,
            "is_active": updated.is_active,
            "category_id": str(updated.category_id)
        }

        # Audit
        await audit_log_repo.create(
            db,
            obj_in={
                "user_id": admin_id,
                "action": "update_app",
                "resource": "apps",
                "old_values": old_values,
                "new_values": new_values
            }
        )
        await db.commit()

        return updated

    async def delete_app(self, db: AsyncSession, app_id: UUID, admin_id: UUID) -> App:
        app = await app_repo.get(db, app_id)
        if not app:
            raise NotFoundException("Application not found")

        # Soft Delete app
        await app_repo.soft_delete(db, id=app_id, updated_by=admin_id)
        
        # Soft delete versions
        for ver in app.versions:
            await app_version_repo.soft_delete(db, id=ver.id, updated_by=admin_id)

        await db.commit()

        # Audit
        await audit_log_repo.create(
            db,
            obj_in={
                "user_id": admin_id,
                "action": "delete_app",
                "resource": "apps",
                "old_values": {"id": str(app_id), "name": app.name}
            }
        )
        await db.commit()

        return app

    async def create_app_version(self, db: AsyncSession, app_id: UUID, data: AppVersionCreate, admin_id: UUID) -> AppVersion:
        app = await app_repo.get(db, app_id)
        if not app:
            raise NotFoundException("Application not found")

        # Validate APK file exists on disk (prevent infected or non-uploaded APKs)
        from pathlib import Path
        from app.core.config import settings
        if not data.apk_url.startswith("/static/apks/"):
            raise ValidationException("Invalid APK URL path. Must begin with /static/apks/")
        
        filename = data.apk_url.replace("/static/apks/", "")
        local_file_path = Path(settings.UPLOAD_DIR) / "apks" / filename
        
        if not local_file_path.exists():
            raise ValidationException(
                "The specified APK file was not found on the server. "
                "It may have been deleted by the anti-virus scanning system or failed to upload."
            )

        # Validate min_sdk_version is a reasonable Android API Level (1 to 35)
        if data.min_sdk_version:
            try:
                sdk_val = int(data.min_sdk_version)
                if sdk_val > 35:
                    raise ValidationException(
                        f"Invalid Minimum SDK level ({sdk_val}). Android API levels range from 1 to 35. "
                        "Please enter a valid Android API Level (e.g. 21 for Android 5.0, 29 for Android 10, 31 for Android 12, 33 for Android 13, 34 for Android 14)."
                    )
            except ValueError:
                # Allow non-integer strings (e.g., "Android 10")
                pass

        # Validate version code is higher
        latest_ver = await app_version_repo.get_latest_version(db, app_id)
        if latest_ver and data.version_code <= latest_ver.version_code:
            raise ValidationException(
                f"Version code must be higher than the current latest version code ({latest_ver.version_code})"
            )

        ver_in = {
            "app_id": app_id,
            "version_code": data.version_code,
            "version_name": data.version_name,
            "apk_url": data.apk_url,
            "apk_size": data.apk_size,
            "release_notes": data.release_notes,
            "min_sdk_version": data.min_sdk_version,
            "permissions": data.permissions or [],
            "sha256": data.sha256,
            "is_active": True
        }

        version = await app_version_repo.create(db, obj_in=ver_in, created_by=admin_id)
        await db.commit()
        await db.refresh(version)

        # Audit
        await audit_log_repo.create(
            db,
            obj_in={
                "user_id": admin_id,
                "action": "create_app_version",
                "resource": "app_versions",
                "new_values": {"app_id": str(app_id), "version_code": version.version_code, "version_name": version.version_name}
            }
        )
        await db.commit()

        return version

    async def get_dashboard_analytics(self, db: AsyncSession) -> DashboardAnalyticsResponse:
        # Total counts
        total_users_q = await db.execute(select(func.count(User.id)).where(User.deleted_at.is_(None)))
        total_users = total_users_q.scalar() or 0

        total_apps_q = await db.execute(select(func.count(App.id)).where(App.deleted_at.is_(None)))
        total_apps = total_apps_q.scalar() or 0

        total_downloads_q = await db.execute(
            select(func.count(Download.id)).where(Download.status == "completed", Download.deleted_at.is_(None))
        )
        total_downloads = total_downloads_q.scalar() or 0

        active_sessions_q = await db.execute(
            select(func.count(UserSession.id)).where(UserSession.is_active == True, UserSession.deleted_at.is_(None))
        )
        active_sessions = active_sessions_q.scalar() or 0

        system_stats = SystemStatsResponse(
            total_users=total_users,
            total_apps=total_apps,
            total_downloads=total_downloads,
            active_sessions=active_sessions
        )

        # Download history (last 14 days)
        fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)
        history_q = await db.execute(
            select(
                func.date_trunc("day", Download.created_at).label("day"),
                func.count(Download.id).label("count")
            )
            .where(
                Download.status == "completed",
                Download.created_at >= fourteen_days_ago,
                Download.deleted_at.is_(None)
            )
            .group_by("day")
            .order_by("day")
        )
        history_results = history_q.all()
        download_history = [
            DownloadStatItem(date=row.day.strftime("%Y-%m-%d"), count=row.count)
            for row in history_results
        ]

        # Category distribution of downloads
        cat_dist_q = await db.execute(
            select(
                Category.name.label("category_name"),
                func.count(Download.id).label("count")
            )
            .join(App, App.category_id == Category.id)
            .join(Download, Download.app_id == App.id)
            .where(Download.status == "completed", Download.deleted_at.is_(None))
            .group_by(Category.name)
        )
        cat_dist_results = cat_dist_q.all()
        category_distribution = [
            CategoryDownloadStat(category_name=row.category_name, count=row.count)
            for row in cat_dist_results
        ]

        # Popular apps (apps sorted by total downloads)
        popular_q = await db.execute(
            select(
                App.id,
                App.name,
                App.developer,
                App.logo_url,
                func.count(Download.id).label("downloads_count")
            )
            .join(Download, Download.app_id == App.id)
            .where(Download.status == "completed", Download.deleted_at.is_(None))
            .group_by(App.id, App.name, App.developer, App.logo_url)
            .order_by(desc("downloads_count"))
            .limit(5)
        )
        popular_results = popular_q.all()
        popular_apps = [
            {
                "id": str(row.id),
                "name": row.name,
                "developer": row.developer,
                "logo_url": row.logo_url,
                "downloads": row.downloads_count
            }
            for row in popular_results
        ]

        return DashboardAnalyticsResponse(
            system_stats=system_stats,
            download_history=download_history,
            category_distribution=category_distribution,
            popular_apps=popular_apps
        )
