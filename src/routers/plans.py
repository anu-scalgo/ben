"""Subscription plans routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..config.database import get_db
from ..services.subscription_service import SubscriptionService
from ..schemas.subscription import PlanSchema, SubscriptionCreate, SubscriptionResponse, QuotaStatus
from ..middleware.auth import get_current_user
from ..middleware.rate_limit import limiter
from fastapi import Request

router = APIRouter(prefix="/plans", tags=["subscriptions"])


@router.get("", response_model=List[PlanSchema])
async def list_plans(db: AsyncSession = Depends(get_db)):
    """Get all available subscription plans."""
    subscription_service = SubscriptionService(db)
    return await subscription_service.get_all_plans()


@router.post("/subscribe", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def subscribe(
    request: Request,
    subscription_data: SubscriptionCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Subscribe to a plan."""
    subscription_service = SubscriptionService(db)
    return await subscription_service.create_subscription(
        user_id=user["id"], subscription_data=subscription_data
    )


@router.get("/quota", response_model=QuotaStatus)
async def get_quota(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current quota status for authenticated user."""
    subscription_service = SubscriptionService(db)
    return await subscription_service.get_quota_status(user_id=user["id"])

