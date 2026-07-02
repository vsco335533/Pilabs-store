from typing import List, Optional
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log import Download, ActivityLog, AuditLog, Notification
from app.repositories.base import BaseRepository


class DownloadRepository(BaseRepository[Download]):
    def __init__(self):
        super().__init__(Download)

    async def get_download_count(self, db: AsyncSession, app_id: str) -> int:
        query = select(func.count(Download.id)).where(
            Download.app_id == app_id,
            Download.status == "completed",
            Download.deleted_at.is_(None)
        )
        result = await db.execute(query)
        return result.scalar() or 0


class ActivityLogRepository(BaseRepository[ActivityLog]):
    def __init__(self):
        super().__init__(ActivityLog)


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self):
        super().__init__(AuditLog)


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self):
        super().__init__(Notification)

    async def get_unread(self, db: AsyncSession, user_id: str) -> List[Notification]:
        query = select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read == False,
            Notification.deleted_at.is_(None)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def mark_all_read(self, db: AsyncSession, user_id: str) -> None:
        query = update(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).values(is_read=True)
        await db.execute(query)
