from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import AuditBase


class User(AuditBase):
    __tablename__ = "users"

    full_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)

    role = relationship("Role", back_populates="users", foreign_keys=[role_id])
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan", foreign_keys="[RefreshToken.user_id]")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan", foreign_keys="[UserSession.user_id]")
    otps = relationship("OTP", back_populates="user", cascade="all, delete-orphan", foreign_keys="[OTP.user_id]")
    password_resets = relationship("PasswordReset", back_populates="user", cascade="all, delete-orphan", foreign_keys="[PasswordReset.user_id]")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan", foreign_keys="[APIKey.user_id]")


class RefreshToken(AuditBase):
    __tablename__ = "refresh_tokens"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(500), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    replaced_by_token = Column(String(500), nullable=True)

    user = relationship("User", back_populates="refresh_tokens", foreign_keys=[user_id])


class UserSession(AuditBase):
    __tablename__ = "user_sessions"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ip_address = Column(String(45), nullable=True)
    device_info = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_activity = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="sessions", foreign_keys=[user_id])


class OTP(AuditBase):
    __tablename__ = "otp"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(10), nullable=False)
    otp_type = Column(String(50), nullable=False)  # 'email_verification', 'password_reset'
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="otps", foreign_keys=[user_id])


class PasswordReset(AuditBase):
    __tablename__ = "password_resets"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="password_resets", foreign_keys=[user_id])


class APIKey(AuditBase):
    __tablename__ = "api_keys"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="api_keys", foreign_keys=[user_id])
