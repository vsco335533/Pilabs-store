from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, EmailStr


class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    phone_number: str
    is_active: bool
    is_verified: bool
    role: RoleResponse
    created_at: datetime
    updated_at: datetime
    otp_code: Optional[str] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None
