from fastapi import APIRouter, Depends, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_async_db
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    OTPVerifyRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest
)
from app.schemas.base import APIResponse
from app.schemas.user import UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=APIResponse[UserResponse])
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_async_db)):
    user, otp_code = await auth_service.register(db, data)
    await db.refresh(user, ["role"])
    user_res = UserResponse.model_validate(user)
    user_res.otp_code = otp_code
    return APIResponse(
        success=True,
        message="Registration successful. Verification OTP sent to email.",
        data=user_res
    )


@router.post("/login")
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    ip_address = request.client.host if request.client else "unknown"
    device_info = request.headers.get("User-Agent", "unknown")
    
    login_data = await auth_service.login(
        db,
        data,
        ip_address=ip_address,
        device_info=device_info
    )
    
    # Map model user to schema user response
    await db.refresh(login_data["user"], ["role"])
    user_res = UserResponse.model_validate(login_data["user"])
    response_payload = {
        "access_token": login_data["access_token"],
        "refresh_token": login_data["refresh_token"],
        "token_type": login_data["token_type"],
        "expires_in": login_data["expires_in"],
        "user": user_res
    }
    
    return APIResponse(
        success=True,
        message="Login successful",
        data=response_payload
    )


@router.post("/refresh")
async def refresh_token(
    data: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    ip_address = request.client.host if request.client else "unknown"
    device_info = request.headers.get("User-Agent", "unknown")
    
    refresh_data = await auth_service.refresh(
        db,
        data.refresh_token,
        ip_address=ip_address,
        device_info=device_info
    )
    
    return APIResponse(
        success=True,
        message="Token refreshed successfully",
        data=refresh_data
    )


@router.post("/verify-otp")
async def verify_otp(data: OTPVerifyRequest, db: AsyncSession = Depends(get_async_db)):
    user = await auth_service.verify_otp(db, data)
    await db.refresh(user, ["role"])
    user_res = UserResponse.model_validate(user)
    return APIResponse(
        success=True,
        message="OTP verified successfully",
        data=user_res
    )


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_async_db)):
    await auth_service.forgot_password(db, data.email_or_phone)
    return APIResponse(
        success=True,
        message="If account exists, reset OTP and email instructions have been sent.",
        data=None
    )


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_async_db)):
    await auth_service.reset_password(db, data.token, data.new_password)
    return APIResponse(
        success=True,
        message="Password has been reset successfully. Please login again.",
        data=None
    )
