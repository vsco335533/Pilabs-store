from app.services.auth import AuthService
from app.services.app import AppService
from app.services.admin import AdminService
from app.services.download import DownloadService

auth_service = AuthService()
app_service = AppService()
admin_service = AdminService()
download_service = DownloadService()

__all__ = [
    "auth_service",
    "app_service",
    "admin_service",
    "download_service",
]
