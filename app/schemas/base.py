from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None


class APIErrorResponse(BaseModel):
    success: bool = False
    message: str
    errors: List[Any] = []


class PaginatedData(BaseModel, Generic[T]):
    items: List[T]
    total: int
    skip: int
    limit: int
