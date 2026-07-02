from app.repositories.user import (
    UserRepository,
    RefreshTokenRepository,
    UserSessionRepository,
    OTPRepository,
    PasswordResetRepository,
)
from app.repositories.role import RoleRepository, PermissionRepository
from app.repositories.app import CategoryRepository, AppRepository, AppVersionRepository
from app.repositories.log import (
    DownloadRepository,
    ActivityLogRepository,
    AuditLogRepository,
    NotificationRepository,
)

# Instantiate repositories as singletons
user_repo = UserRepository()
refresh_token_repo = RefreshTokenRepository()
user_session_repo = UserSessionRepository()
otp_repo = OTPRepository()
password_reset_repo = PasswordResetRepository()

role_repo = RoleRepository()
permission_repo = PermissionRepository()

category_repo = CategoryRepository()
app_repo = AppRepository()
app_version_repo = AppVersionRepository()

download_repo = DownloadRepository()
activity_log_repo = ActivityLogRepository()
audit_log_repo = AuditLogRepository()
notification_repo = NotificationRepository()

__all__ = [
    "user_repo",
    "refresh_token_repo",
    "user_session_repo",
    "otp_repo",
    "password_reset_repo",
    "role_repo",
    "permission_repo",
    "category_repo",
    "app_repo",
    "app_version_repo",
    "download_repo",
    "activity_log_repo",
    "audit_log_repo",
    "notification_repo",
]
