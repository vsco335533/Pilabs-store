from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

ph = PasswordHasher()


def get_password_hash(password: str) -> str:
    """Hash password using Argon2"""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify Argon2 password hash"""
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False


def create_jwt_token(
    subject: Union[str, Any],
    secret_key: str,
    expires_delta: timedelta,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """Create a signed JWT token"""
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    payload = {
        "iss": settings.PROJECT_NAME,
        "sub": str(subject),
        "iat": now,
        "exp": expire,
    }
    if additional_claims:
        payload.update(additional_claims)
    return jwt.encode(payload, secret_key, algorithm="HS256")


def create_access_token(
    subject: Union[str, Any],
    role: str,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """Create an access token (shorter life)"""
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    claims = {"role": role}
    if additional_claims:
        claims.update(additional_claims)
    return create_jwt_token(
        subject=subject,
        secret_key=settings.SECRET_KEY,
        expires_delta=expires,
        additional_claims=claims
    )


def create_refresh_token(subject: Union[str, Any]) -> str:
    """Create a refresh token (longer life)"""
    expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return create_jwt_token(
        subject=subject,
        secret_key=settings.REFRESH_SECRET_KEY,
        expires_delta=expires,
        additional_claims={"type": "refresh"}
    )


def verify_token(token: str, secret_key: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=["HS256"],
            issuer=settings.PROJECT_NAME
        )
        return payload
    except jwt.PyJWTError:
        return None
