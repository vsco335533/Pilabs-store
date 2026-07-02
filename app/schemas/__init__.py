from app.schemas.base import APIResponse, APIErrorResponse, PaginatedData
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    OTPVerifyRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.schemas.user import UserResponse, UserUpdate, RoleResponse
from app.schemas.app import (
    CategoryResponse,
    CategoryCreate,
    AppResponse,
    AppCreate,
    AppUpdate,
    AppVersionResponse,
    AppVersionCreate,
    AppDetailResponse,
)
from app.schemas.admin import (
    SystemStatsResponse,
    DashboardAnalyticsResponse,
    DownloadStatItem,
    CategoryDownloadStat,
)

__all__ = [
    "APIResponse",
    "APIErrorResponse",
    "PaginatedData",
    "RegisterRequest",
    "LoginRequest",
    "RefreshTokenRequest",
    "OTPVerifyRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "UserResponse",
    "UserUpdate",
    "RoleResponse",
    "CategoryResponse",
    "CategoryCreate",
    "AppResponse",
    "AppCreate",
    "AppUpdate",
    "AppVersionResponse",
    "AppVersionCreate",
    "AppDetailResponse",
    "SystemStatsResponse",
    "DashboardAnalyticsResponse",
    "DownloadStatItem",
    "CategoryDownloadStat",
]
