"""Shared base schemas and common models."""

from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema."""

    items: List[T]
    total: int
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    total_pages: int

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int = 1,
        page_size: int = 20,
    ) -> "PaginatedResponse[T]":
        """Create paginated response with calculated total_pages."""
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    detail: str
    error_code: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response schema."""

    message: str
    data: Optional[dict] = None

