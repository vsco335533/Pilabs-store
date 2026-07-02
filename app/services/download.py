import logging
from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.custom_exceptions import NotFoundException
from app.models.log import Download
from app.repositories import download_repo, app_repo, app_version_repo, activity_log_repo

logger = logging.getLogger(__name__)


class DownloadService:
    async def initiate_download(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        app_id: UUID,
        version_id: UUID,
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None
    ) -> Download:
        # Validate App and Version exist
        app = await app_repo.get(db, app_id)
        if not app:
            raise NotFoundException("App not found")

        version = await app_version_repo.get(db, version_id)
        if not version or version.app_id != app_id:
            raise NotFoundException("App version not found")

        # Create Download record
        download = await download_repo.create(
            db,
            obj_in={
                "user_id": user_id,
                "app_id": app_id,
                "version_id": version_id,
                "ip_address": ip_address,
                "device_info": device_info,
                "status": "started"
            }
        )
        await db.commit()

        # Log Activity
        await activity_log_repo.create(
            db,
            obj_in={
                "user_id": user_id,
                "action": "download_start",
                "description": f"Started downloading app: {app.name} (v{version.version_name})",
                "meta_data": {"app_id": str(app_id), "version_id": str(version_id)}
            }
        )
        await db.commit()

        return download

    async def complete_download(self, db: AsyncSession, download_id: UUID) -> Download:
        download = await download_repo.get(db, download_id)
        if not download:
            raise NotFoundException("Download record not found")

        download.status = "completed"
        db.add(download)
        await db.commit()

        # Log Activity
        await activity_log_repo.create(
            db,
            obj_in={
                "user_id": download.user_id,
                "action": "download_complete",
                "description": f"Completed downloading app ID: {download.app_id}",
                "meta_data": {"download_id": str(download_id)}
            }
        )
        await db.commit()

        return download

    async def fail_download(self, db: AsyncSession, download_id: UUID) -> Download:
        download = await download_repo.get(db, download_id)
        if not download:
            raise NotFoundException("Download record not found")

        download.status = "failed"
        db.add(download)
        await db.commit()
        return download
