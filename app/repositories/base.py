from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        """Fetch a single record by ID, excluding soft deleted ones"""
        query = select(self.model).where(
            self.model.id == id,
            self.model.deleted_at.is_(None)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[ModelType]:
        """Fetch multiple records with offset pagination"""
        query = select(self.model)
        if not include_deleted and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: Dict[str, Any], created_by: Optional[Any] = None) -> ModelType:
        """Create a new database record"""
        if created_by and hasattr(self.model, "created_by"):
            obj_in["created_by"] = created_by
            obj_in["updated_by"] = created_by
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.flush()
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[Dict[str, Any], Any],
        updated_by: Optional[Any] = None
    ) -> ModelType:
        """Update an existing record"""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        if updated_by and hasattr(self.model, "updated_by"):
            update_data["updated_by"] = updated_by

        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])

        db.add(db_obj)
        await db.flush()
        return db_obj

    async def remove(self, db: AsyncSession, *, id: Any) -> Optional[ModelType]:
        """Permanently delete a record"""
        query = select(self.model).where(self.model.id == id)
        result = await db.execute(query)
        obj = result.scalar_one_or_none()
        if obj:
            await db.delete(obj)
            await db.flush()
        return obj

    async def soft_delete(self, db: AsyncSession, *, id: Any, updated_by: Optional[Any] = None) -> Optional[ModelType]:
        """Mark record as soft-deleted"""
        query = select(self.model).where(
            self.model.id == id,
            self.model.deleted_at.is_(None)
        )
        result = await db.execute(query)
        obj = result.scalar_one_or_none()
        if obj and hasattr(obj, "soft_delete"):
            obj.soft_delete()
            if updated_by and hasattr(obj, "updated_by"):
                obj.updated_by = updated_by
            db.add(obj)
            await db.flush()
        return obj
