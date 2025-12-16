"""Quota checking middleware for subscription limits."""

from typing import Callable
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..config.database import get_db
from ..middleware.auth import get_current_user
from ..repositories.subscription_repo import SubscriptionRepository
from ..utils.constants import PlanTier


async def check_quota(
    required_storage_gb: float = 0.0,
    required_files: int = 0,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Dependency to check if user has sufficient quota.
    Raises HTTPException if quota exceeded.
    Args:
        required_storage_gb: Required storage in GB
        required_files: Required number of files
        user: Current authenticated user
        db: Database session
    Returns:
        User subscription data
    """
    subscription_repo = SubscriptionRepository(db)
    subscription = await subscription_repo.get_by_user_id(user["id"])

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active subscription found",
        )

    # Check storage quota
    if subscription["used_storage_gb"] + required_storage_gb > subscription["storage_limit_gb"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Storage quota exceeded. Available: {subscription['storage_limit_gb'] - subscription['used_storage_gb']:.2f} GB",
        )

    # Check file count quota
    if subscription["used_file_count"] + required_files > subscription["file_limit"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"File count quota exceeded. Available: {subscription['file_limit'] - subscription['used_file_count']} files",
        )

    return subscription


async def check_plan_tier(
    required_tier: PlanTier,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Dependency to check if user's plan tier meets requirements.
    Raises HTTPException if tier is insufficient.
    """
    subscription_repo = SubscriptionRepository(db)
    subscription = await subscription_repo.get_by_user_id(user["id"])

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active subscription found",
        )

    user_tier = PlanTier(subscription["plan_tier"])
    if user_tier.value < required_tier.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This feature requires {required_tier.name} plan or higher",
        )

    return subscription

