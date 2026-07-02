from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, BigInteger, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import AuditBase


class Category(AuditBase):
    __tablename__ = "categories"

    name = Column(String(100), unique=True, nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)

    apps = relationship("App", back_populates="category")


class App(AuditBase):
    __tablename__ = "apps"

    name = Column(String(150), nullable=False, index=True)
    slug = Column(String(150), unique=True, nullable=False, index=True)
    package_name = Column(String(255), unique=True, nullable=False, index=True)
    developer = Column(String(150), nullable=False)
    description = Column(String(1000), nullable=True)
    logo_url = Column(String(500), nullable=True)
    screenshots = Column(JSON, nullable=True)  # List of URLs
    is_active = Column(Boolean, default=True, nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)

    category = relationship("Category", back_populates="apps")
    versions = relationship("AppVersion", back_populates="app", cascade="all, delete-orphan")
    downloads = relationship("Download", back_populates="app")


class AppVersion(AuditBase):
    __tablename__ = "app_versions"

    app_id = Column(UUID(as_uuid=True), ForeignKey("apps.id", ondelete="CASCADE"), nullable=False)
    version_code = Column(Integer, nullable=False, index=True)
    version_name = Column(String(50), nullable=False)
    apk_url = Column(String(500), nullable=False)
    apk_size = Column(BigInteger, nullable=False)  # in bytes
    release_notes = Column(String(2000), nullable=True)
    min_sdk_version = Column(String(50), nullable=True)
    permissions = Column(JSON, nullable=True)  # List of permissions required
    sha256 = Column(String(64), nullable=False)  # SHA-256 integrity hash
    is_active = Column(Boolean, default=True, nullable=False)

    app = relationship("App", back_populates="versions")
