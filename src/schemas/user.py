"""User schemas."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from ..models.user import UserRole


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    full_name: str
    is_active: bool = True


class UserCreate(UserBase):
    """User creation schema (admin)."""

    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.ENDUSER


class UserUpdate(BaseModel):
    """User update schema."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None
    password: Optional[str] = Field(None, min_length=8)
