"""Subscription and plan schemas."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from ..utils.constants import PlanTier


class PlanSchema(BaseModel):
    """Subscription plan schema."""

    id: int
    name: str
    tier: PlanTier
    price_monthly: float = Field(..., ge=0, description="Monthly price in USD")
    storage_limit_gb: float = Field(..., ge=0, description="Storage limit in GB")
    file_limit: int = Field(..., ge=0, description="Maximum number of files")
    features: list[str] = Field(default_factory=list)
    is_active: bool = True

    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    """Create subscription request schema."""

    plan_id: int
    stripe_payment_method_id: Optional[str] = None


class SubscriptionResponse(BaseModel):
    """Subscription response schema."""

    id: int
    user_id: int
    plan_id: int
    plan_tier: PlanTier
    status: str
    storage_limit_gb: float
    used_storage_gb: float
    file_limit: int
    used_file_count: int
    current_period_start: datetime
    current_period_end: datetime
    stripe_subscription_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuotaStatus(BaseModel):
    """Quota status response schema."""

    storage_limit_gb: float
    used_storage_gb: float
    available_storage_gb: float
    storage_percentage_used: float
    file_limit: int
    used_file_count: int
    available_file_count: int
    file_percentage_used: float

