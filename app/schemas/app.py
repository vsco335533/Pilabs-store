from datetime import datetime
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, Field


class CategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=255)


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: UUID
    slug: str
    created_at: datetime

    class Config:
        from_attributes = True


class AppVersionBase(BaseModel):
    version_code: int
    version_name: str = Field(..., max_length=50)
    apk_url: str = Field(..., max_length=500)
    apk_size: int
    release_notes: Optional[str] = Field(None, max_length=2000)
    min_sdk_version: Optional[str] = Field(None, max_length=50)
    permissions: Optional[List[str]] = None
    sha256: str = Field(..., max_length=64)


class AppVersionCreate(AppVersionBase):
    pass


class AppVersionResponse(AppVersionBase):
    id: UUID
    app_id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AppBase(BaseModel):
    name: str = Field(..., max_length=150)
    package_name: str = Field(..., max_length=255)
    developer: str = Field(..., max_length=150)
    description: Optional[str] = Field(None, max_length=1000)
    logo_url: Optional[str] = Field(None, max_length=500)
    screenshots: Optional[List[str]] = None
    category_id: UUID


class AppCreate(AppBase):
    pass


class AppUpdate(BaseModel):
    name: Optional[str] = None
    package_name: Optional[str] = None
    developer: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    screenshots: Optional[List[str]] = None
    is_active: Optional[bool] = None
    category_id: Optional[UUID] = None


class AppResponse(AppBase):
    id: UUID
    slug: str
    is_active: bool
    created_at: datetime
    category: CategoryResponse
    latest_version: Optional[AppVersionResponse] = None
    versions: Optional[List[AppVersionResponse]] = []

    class Config:
        from_attributes = True


class AppDetailResponse(AppResponse):
    downloads_count: int = 0
    rating: float = 4.5  # placeholder or calculated
    update_available: bool = False
