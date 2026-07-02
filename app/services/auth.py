import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.exceptions.custom_exceptions import (
    ConflictException,
    AuthenticationException,
    NotFoundException,
    ValidationException
)
from app.models.user import User, UserSession, RefreshToken
from app.repositories import (
    user_repo,
    role_repo,
    refresh_token_repo,
    user_session_repo,
    otp_repo,
    password_reset_repo,
    activity_log_repo
)
from app.schemas.auth import RegisterRequest, LoginRequest, OTPVerifyRequest
from app.security.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token
)

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("audit")


class AuthService:
    async def register(self, db: AsyncSession, data: RegisterRequest) -> User:
        # Check email
        existing_user = await user_repo.get_by_email(db, data.email)
        if existing_user:
            raise ConflictException("Email already registered")

        # Check phone number
        existing_phone = await user_repo.get_by_phone_number(db, data.phone_number)
        if existing_phone:
            raise ConflictException("Phone number already registered")

        # Get default User role
        role = await role_repo.get_by_name(db, "User")
        if not role:
            # Fallback if roles seed hasn't run
            role = await role_repo.create(db, obj_in={"name": "User", "description": "Standard App Store User"})

        # Hash password
        hashed_password = get_password_hash(data.password)

        # Create user
        user_in = {
            "full_name": data.full_name,
            "email": data.email,
            "phone_number": data.phone_number,
            "password_hash": hashed_password,
            "role_id": role.id,
            "is_active": True,
            "is_verified": False
        }
        user = await user_repo.create(db, obj_in=user_in)
        await db.commit()
        await db.refresh(user)

        # Generate OTP for email verification (example: 6 digits)
        otp_code = str(uuid.uuid4().int)[:6]
        otp_expires = datetime.now(timezone.utc) + timedelta(minutes=15)
        await otp_repo.create(
            db,
            obj_in={
                "user_id": user.id,
                "code": otp_code,
                "otp_type": "email_verification",
                "expires_at": otp_expires
            }
        )
        await db.commit()

        # Log action
        await activity_log_repo.create(
            db,
            obj_in={
                "user_id": user.id,
                "action": "register",
                "description": f"User registered: {user.email}",
                "meta_data": {"email": user.email}
            }
        )
        await db.commit()

        audit_logger.info(f"AUDIT: User registered successfully: {user.id} ({user.email})")
        logger.info(f"Sent email verification OTP to {user.email} (Mocked OTP: {otp_code})")

        # Send email via Brevo
        from app.utils.email import send_otp_email
        await send_otp_email(user.email, otp_code, "email_verification")

        # Fetch user with selectinload(User.role) to prevent MissingGreenlet in pydantic serialization
        refreshed_user = await user_repo.get(db, user.id)
        return refreshed_user, otp_code

    async def login(
        self,
        db: AsyncSession,
        data: LoginRequest,
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None
    ) -> Dict[str, Any]:
        # Fetch user by email or phone
        user = None
        if "@" in data.email_or_phone:
            user = await user_repo.get_by_email(db, data.email_or_phone)
        else:
            user = await user_repo.get_by_phone_number(db, data.email_or_phone)

        if not user:
            raise AuthenticationException("Invalid email/phone or password")

        if not user.is_active:
            raise AuthenticationException("User account is deactivated")

        # Verify password
        if not verify_password(data.password, user.password_hash):
            raise AuthenticationException("Invalid email/phone or password")

        # Deactivate previous sessions if not remember_me to keep session counts low
        if not data.remember_me:
            await user_session_repo.deactivate_all_user_sessions(db, user.id)

        # Create user session
        session = await user_session_repo.create(
            db,
            obj_in={
                "user_id": user.id,
                "ip_address": ip_address,
                "device_info": device_info,
                "is_active": True,
                "last_activity": datetime.now(timezone.utc)
            }
        )

        # Generate tokens
        await db.refresh(user, ["role"])
        access_token = create_access_token(subject=user.id, role=user.role.name)
        refresh_token = create_refresh_token(subject=user.id)

        # Save refresh token
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await refresh_token_repo.create(
            db,
            obj_in={
                "user_id": user.id,
                "token": refresh_token,
                "expires_at": expires_at
            }
        )
        await db.commit()

        # Log Activity
        await activity_log_repo.create(
            db,
            obj_in={
                "user_id": user.id,
                "action": "login",
                "description": f"User logged in from {ip_address or 'Unknown IP'}",
                "ip_address": ip_address,
                "device_info": device_info
            }
        )
        await db.commit()

        audit_logger.info(f"AUDIT: User logged in: {user.id} ({user.email}) from {ip_address}")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": user
        }

    async def refresh(
        self,
        db: AsyncSession,
        token: str,
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None
    ) -> Dict[str, Any]:
        # Verify Token structure
        payload = verify_token(token, settings.REFRESH_SECRET_KEY)
        if not payload or payload.get("type") != "refresh":
            raise AuthenticationException("Invalid or expired refresh token")

        # Find in DB
        db_token = await refresh_token_repo.get_by_token(db, token)
        if not db_token or db_token.is_revoked or db_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            # If token is reused and was already revoked, this is a breach! Revoke ALL tokens of this user
            if db_token and db_token.is_revoked:
                await refresh_token_repo.revoke_user_tokens(db, db_token.user_id)
                await user_session_repo.deactivate_all_user_sessions(db, db_token.user_id)
                await db.commit()
                audit_logger.warning(f"AUDIT WARN: Reuse of revoked refresh token detected for User: {db_token.user_id}. Revoked all tokens.")
            raise AuthenticationException("Invalid or expired refresh token")

        await db.refresh(db_token, ["user"])
        user = db_token.user
        if not user or not user.is_active:
            raise AuthenticationException("User deactivated or not found")
        await db.refresh(user, ["role"])

        # Rotate Refresh Token (RTR)
        # 1. Revoke the current token
        db_token.is_revoked = True
        db_token.updated_at = datetime.now(timezone.utc)

        # 2. Generate new tokens
        new_access_token = create_access_token(subject=user.id, role=user.role.name)
        new_refresh_token = create_refresh_token(subject=user.id)

        # 3. Associate and save new token
        db_token.replaced_by_token = new_refresh_token
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await refresh_token_repo.create(
            db,
            obj_in={
                "user_id": user.id,
                "token": new_refresh_token,
                "expires_at": expires_at
            }
        )

        # 4. Update session activity
        sessions = await user_session_repo.get_active_sessions(db, user.id)
        if sessions:
            # update last activity on the latest session
            latest_session = sessions[-1]
            latest_session.last_activity = datetime.now(timezone.utc)
            if ip_address:
                latest_session.ip_address = ip_address
            if device_info:
                latest_session.device_info = device_info
            db.add(latest_session)

        await db.commit()

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    async def verify_otp(self, db: AsyncSession, data: OTPVerifyRequest) -> User:
        user = None
        if "@" in data.email_or_phone:
            user = await user_repo.get_by_email(db, data.email_or_phone)
        else:
            user = await user_repo.get_by_phone_number(db, data.email_or_phone)

        if not user:
            raise NotFoundException("User not found")

        # Verify OTP
        # Fallback master OTP code for testing and environments where email API blocks Render IP
        if data.code == "123456":
            otp_rec = None
        else:
            otp_rec = await otp_repo.get_valid_otp(db, user.id, data.code, data.otp_type)
            if not otp_rec:
                raise ValidationException("Invalid or expired OTP code")

        # Mark OTP as used
        if otp_rec:
            otp_rec.is_used = True
            db.add(otp_rec)

        # Action based on OTP Type
        if data.otp_type == "email_verification":
            user.is_verified = True
            db.add(user)

        await db.commit()

        # Log Activity
        await activity_log_repo.create(
            db,
            obj_in={
                "user_id": user.id,
                "action": "verify_otp",
                "description": f"Verified OTP successfully for {data.otp_type}"
            }
        )
        await db.commit()
        return user

    async def forgot_password(self, db: AsyncSession, email_or_phone: str) -> None:
        user = None
        if "@" in email_or_phone:
            user = await user_repo.get_by_email(db, email_or_phone)
        else:
            user = await user_repo.get_by_phone_number(db, email_or_phone)

        if not user:
            # For security, we don't throw an error indicating email/phone doesn't exist.
            # We just return silently so attackers cannot harvest usernames.
            logger.info(f"Forgot password requested for non-existing identifier: {email_or_phone}")
            return

        # Create Password Reset token (using standard uuid format)
        token = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await password_reset_repo.create(
            db,
            obj_in={
                "user_id": user.id,
                "token": token,
                "expires_at": expires_at
            }
        )
        await db.commit()

        # Generate custom OTP for mobile app forgot password screen too (simulating user convenience)
        otp_code = str(uuid.uuid4().int)[:6]
        await otp_repo.create(
            db,
            obj_in={
                "user_id": user.id,
                "code": otp_code,
                "otp_type": "password_reset",
                "expires_at": expires_at
            }
        )
        await db.commit()

        logger.info(f"Sent password reset OTP: {otp_code} and Reset Token: {token} to user {user.email}")

        # Send email via Brevo
        from app.utils.email import send_otp_email
        await send_otp_email(user.email, otp_code, "password_reset")

    async def reset_password(self, db: AsyncSession, token: str, new_password: str) -> None:
        reset_rec = await password_reset_repo.get_by_token(db, token)
        if not reset_rec:
            raise ValidationException("Invalid or expired password reset token")

        user = reset_rec.user
        if not user or not user.is_active:
            raise NotFoundException("User not found or deactivated")

        # Hash new password
        user.password_hash = get_password_hash(new_password)
        db.add(user)

        # Mark reset token as used
        reset_rec.is_used = True
        db.add(reset_rec)

        # Security precaution: Revoke all tokens & active sessions
        await refresh_token_repo.revoke_user_tokens(db, user.id)
        await user_session_repo.deactivate_all_user_sessions(db, user.id)
        await db.commit()

        audit_logger.info(f"AUDIT: Password reset successfully completed for User: {user.id}")
