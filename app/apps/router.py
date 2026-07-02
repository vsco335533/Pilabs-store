from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.core.database import get_async_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.app import AppResponse, AppDetailResponse, CategoryResponse
from app.schemas.base import APIResponse
from app.services import app_service, download_service

router = APIRouter(prefix="/apps", tags=["Applications"])


@router.get("/categories", response_model=APIResponse[List[CategoryResponse]])
async def get_categories(db: AsyncSession = Depends(get_async_db)):
    categories = await app_service.list_categories(db)
    return APIResponse(
        success=True,
        message="Categories retrieved successfully",
        data=categories
    )


@router.get("", response_model=APIResponse[List[AppResponse]])
async def get_apps(
    query: Optional[str] = Query(None, description="Search query"),
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: AsyncSession = Depends(get_async_db)
):
    apps = await app_service.list_apps(
        db,
        query=query,
        category_id=category_id,
        skip=skip,
        limit=limit
    )
    return APIResponse(
        success=True,
        message="Applications retrieved successfully",
        data=apps
    )


@router.get("/featured", response_model=APIResponse[List[AppResponse]])
async def get_featured_apps(
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_async_db)
):
    apps = await app_service.get_featured(db, limit=limit)
    return APIResponse(
        success=True,
        message="Featured applications retrieved successfully",
        data=apps
    )


@router.get("/latest", response_model=APIResponse[List[AppResponse]])
async def get_latest_apps(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db)
):
    apps = await app_service.get_latest(db, limit=limit)
    return APIResponse(
        success=True,
        message="Latest applications retrieved successfully",
        data=apps
    )


@router.get("/{id_or_slug}", response_model=APIResponse[AppDetailResponse])
async def get_app_details(
    id_or_slug: str,
    db: AsyncSession = Depends(get_async_db)
):
    app = await app_service.get_app_details(db, id_or_slug)
    return APIResponse(
        success=True,
        message="Application details retrieved successfully",
        data=app
    )


@router.post("/{app_id}/versions/{version_id}/download")
async def track_app_download(
    app_id: UUID,
    version_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    ip_address = request.client.host if request.client else "unknown"
    device_info = request.headers.get("User-Agent", "unknown")
    
    download_rec = await download_service.initiate_download(
        db,
        user_id=current_user.id,
        app_id=app_id,
        version_id=version_id,
        ip_address=ip_address,
        device_info=device_info
    )
    
    # Simulate immediate completion for basic download tracking
    await download_service.complete_download(db, download_rec.id)
    
    return APIResponse(
        success=True,
        message="Download tracked successfully",
        data={"download_id": str(download_rec.id)}
    )
