"""DumaPod schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field
from ..models.dumapod import StorageProvider


class DumaPodBase(BaseModel):
    """Base schema for DumaPod."""

    name: str = Field(..., min_length=3, max_length=100)
    storage_capacity_gb: int = Field(..., gt=0)
    
    enable_s3: bool = False
    enable_wasabi: bool = False
    enable_oracle_os: bool = False
    
    primary_storage: StorageProvider
    secondary_storage: Optional[StorageProvider] = None
    
    amount_in_usd: Decimal = Field(..., ge=0)
    is_active: bool = True


class DumaPodCreate(DumaPodBase):
    """Schema for creating a DumaPod."""
    pass


class DumaPodUpdate(BaseModel):
    """Schema for updating a DumaPod."""
    
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    storage_capacity_gb: Optional[int] = Field(None, gt=0)
    
    enable_s3: Optional[bool] = None
    enable_wasabi: Optional[bool] = None
    enable_oracle_os: Optional[bool] = None
    
    primary_storage: Optional[StorageProvider] = None
    secondary_storage: Optional[StorageProvider] = None
    
    amount_in_usd: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None


class DumaPodResponse(DumaPodBase):
    """Schema for DumaPod response."""
    
    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
