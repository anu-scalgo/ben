"""Pod Category schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PodCategoryBase(BaseModel):
    """Base schema for Pod Category."""

    name: str = Field(..., min_length=2, max_length=100)
    is_active: bool = True


class PodCategoryCreate(PodCategoryBase):
    """Schema for creating a Pod Category."""
    pass


class PodCategoryUpdate(BaseModel):
    """Schema for updating a Pod Category."""
    
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    is_active: Optional[bool] = None


class PodCategoryResponse(PodCategoryBase):
    """Schema for Pod Category response."""
    
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
