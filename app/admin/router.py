import hashlib
import os
import shutil
from pathlib import Path
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_async_db
from app.dependencies.auth import require_admin
from app.models.user import User
from app.models.log import AuditLog
from app.schemas.admin import DashboardAnalyticsResponse
from app.schemas.app import (
    AppResponse,
    AppCreate,
    AppUpdate,
    AppVersionResponse,
    AppVersionCreate,
    CategoryResponse,
    CategoryCreate
)
from app.schemas.base import APIResponse
from app.schemas.user import UserResponse
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["Admin Portal"], dependencies=[Depends(require_admin)])


@router.post("/categories", response_model=APIResponse[CategoryResponse])
async def create_category(
    data: CategoryCreate,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db)
):
    category = await admin_service.create_category(db, data, current_admin.id)
    return APIResponse(
        success=True,
        message="Category created successfully",
        data=CategoryResponse.model_validate(category)
    )


@router.post("/apps", response_model=APIResponse[AppResponse])
async def create_app(
    data: AppCreate,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db)
):
    app = await admin_service.create_app(db, data, current_admin.id)
    return APIResponse(
        success=True,
        message="Application registered successfully",
        data=AppResponse.model_validate(app)
    )


@router.patch("/apps/{app_id}", response_model=APIResponse[AppResponse])
async def update_app(
    app_id: UUID,
    data: AppUpdate,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db)
):
    app = await admin_service.update_app(db, app_id, data, current_admin.id)
    return APIResponse(
        success=True,
        message="Application updated successfully",
        data=AppResponse.model_validate(app)
    )


@router.delete("/apps/{app_id}", response_model=APIResponse[None])
async def delete_app(
    app_id: UUID,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db)
):
    await admin_service.delete_app(db, app_id, current_admin.id)
    return APIResponse(
        success=True,
        message="Application deleted successfully",
        data=None
    )


@router.post("/apps/{app_id}/versions", response_model=APIResponse[AppVersionResponse])
async def create_app_version(
    app_id: UUID,
    data: AppVersionCreate,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db)
):
    version = await admin_service.create_app_version(db, app_id, data, current_admin.id)
    return APIResponse(
        success=True,
        message="New version released successfully",
        data=AppVersionResponse.model_validate(version)
    )


@router.get("/statistics", response_model=APIResponse[DashboardAnalyticsResponse])
async def get_dashboard_analytics(
    db: AsyncSession = Depends(get_async_db)
):
    stats = await admin_service.get_dashboard_analytics(db)
    return APIResponse(
        success=True,
        message="Dashboard statistics retrieved successfully",
        data=stats
    )


@router.get("/users", response_model=APIResponse[List[UserResponse]])
async def list_users(
    db: AsyncSession = Depends(get_async_db)
):
    query = select(User).where(User.deleted_at.is_(None)).options(selectinload(User.role))
    result = await db.execute(query)
    users = result.scalars().all()
    return APIResponse(
        success=True,
        message="Users list retrieved",
        data=[UserResponse.model_validate(u) for u in users]
    )


@router.get("/audit-logs", response_model=APIResponse[List[dict]])
async def list_audit_logs(
    db: AsyncSession = Depends(get_async_db)
):
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)
    result = await db.execute(query)
    logs = result.scalars().all()
    
    logs_data = []
    for log in logs:
        logs_data.append({
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource": log.resource,
            "old_values": log.old_values,
            "new_values": log.new_values,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat()
        })
        
    return APIResponse(
        success=True,
        message="Audit logs retrieved",
        data=logs_data
    )


# File upload endpoints
@router.post("/upload/apk")
async def upload_apk(
    file: UploadFile = File(...)
):
    # Validate file type
    if not file.filename.endswith(".apk"):
        raise HTTPException(status_code=400, detail="Only .apk files are allowed")

    # Create directories
    apk_dir = Path(settings.UPLOAD_DIR) / "apks"
    apk_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = apk_dir / file.filename
    
    # Save file and calculate SHA-256
    sha256_hash = hashlib.sha256()
    size = 0
    
    try:
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(8192):
                buffer.write(chunk)
                sha256_hash.update(chunk)
                size += len(chunk)
    except Exception as e:
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to save APK file: {str(e)}")

    sha256_checksum = sha256_hash.hexdigest()
    
    # Trigger background anti-virus scanning
    from app.core.celery import scan_apk_file
    scan_apk_file.delay(str(file_path.resolve()))
    
    # Return file url (will be served statically by main FastAPI app)
    # Using format: /static/apks/{filename}
    apk_url = f"/static/apks/{file.filename}"
    
    return APIResponse(
        success=True,
        message="APK uploaded successfully. Scan scheduled.",
        data={
            "apk_url": apk_url,
            "apk_size": size,
            "sha256": sha256_checksum
        }
    )


@router.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...)
):
    # Validate extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        raise HTTPException(status_code=400, detail="Only PNG, JPG, JPEG, or WEBP images are allowed")

    # Create directories
    img_dir = Path(settings.UPLOAD_DIR) / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = img_dir / file.filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to save image: {str(e)}")

    image_url = f"/static/images/{file.filename}"
    
    return APIResponse(
        success=True,
        message="Image uploaded successfully",
        data={
            "image_url": image_url
        }
    )
