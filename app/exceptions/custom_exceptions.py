from typing import Any, List, Optional


class AppException(Exception):
    """Base application exception"""
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        errors: Optional[List[Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.errors = errors or []
        super().__init__(message)


class AuthenticationException(AppException):
    def __init__(self, message: str = "Authentication failed", errors: Optional[List[Any]] = None):
        super().__init__(message, status_code=401, errors=errors)


class AuthorizationException(AppException):
    def __init__(self, message: str = "Permission denied", errors: Optional[List[Any]] = None):
        super().__init__(message, status_code=403, errors=errors)


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", errors: Optional[List[Any]] = None):
        super().__init__(message, status_code=404, errors=errors)


class ConflictException(AppException):
    def __init__(self, message: str = "Conflict occurred", errors: Optional[List[Any]] = None):
        super().__init__(message, status_code=409, errors=errors)


class ValidationException(AppException):
    def __init__(self, message: str = "Validation failed", errors: Optional[List[Any]] = None):
        super().__init__(message, status_code=422, errors=errors)


class RateLimitException(AppException):
    def __init__(self, message: str = "Too many requests", errors: Optional[List[Any]] = None):
        super().__init__(message, status_code=429, errors=errors)
