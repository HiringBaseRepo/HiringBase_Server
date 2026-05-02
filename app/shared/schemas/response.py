"""Standard API response schemas."""
from typing import Any, Dict, List, Optional, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool


class StandardResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Success"
    data: Optional[T] = None
    errors: Optional[List[Dict[str, Any]]] = None
    meta: Optional[Dict[str, Any]] = None

    @classmethod
    def ok(cls, data: Any = None, message: str = "Success", meta: Dict = None):
        return cls(success=True, message=message, data=data, meta=meta)

    @classmethod
    def error(cls, message: str = "Error", errors: List[Dict] = None, status_code: int = 400):
        return cls(success=False, message=message, errors=errors or [])
