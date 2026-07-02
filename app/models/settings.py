from sqlalchemy import Column, String
from app.models.base import AuditBase


class SystemSettings(AuditBase):
    __tablename__ = "system_settings"

    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(String(1000), nullable=False)
    description = Column(String(255), nullable=True)
