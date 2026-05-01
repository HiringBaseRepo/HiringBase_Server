"""Pagination helpers."""
from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = 1
    per_page: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page


class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool
