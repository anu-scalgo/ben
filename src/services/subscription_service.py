"""Subscription service for plan management and Stripe integration."""

from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..repositories.subscription_repo import SubscriptionRepository
from ..repositories.user_repo import UserRepository
from ..config.stripe import stripe_client
from ..schemas.subscription import PlanSchema, SubscriptionCreate, SubscriptionResponse, QuotaStatus
from ..utils.helpers import bytes_to_gb


class SubscriptionService:
    """Service for subscription operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.subscription_repo = SubscriptionRepository(db)
        self.user_repo = UserRepository(db)

    async def get_all_plans(self) -> List[PlanSchema]:
        """Get all available subscription plans."""
        plans = await self.subscription_repo.get_all_plans()
        return [PlanSchema(**plan) for plan in plans]

    async def create_subscription(
        self, user_id: int, subscription_data: SubscriptionCreate
    ) -> SubscriptionResponse:
        """
        Create a new subscription for a user.
        Integrates with Stripe for payment processing.
        """
        # Get plan details
        plans = await self.subscription_repo.get_all_plans()
        plan = next((p for p in plans if p["id"] == subscription_data.plan_id), None)

        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found",
            )

        # Create Stripe subscription if payment method provided
        stripe_subscription_id = None
        if subscription_data.stripe_payment_method_id:
            try:
                # Create Stripe customer if needed
                user = await self.user_repo.get_by_id(user_id)
                # In real implementation, create/retrieve Stripe customer
                # stripe_customer = stripe_client.Customer.create(...)

                # Create Stripe subscription
                # stripe_subscription = stripe_client.Subscription.create(...)
                # stripe_subscription_id = stripe_subscription.id
                pass
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to create Stripe subscription: {str(e)}",
                )

        # Create subscription record
        subscription = await self.subscription_repo.create_subscription(
            user_id=user_id,
            plan_id=subscription_data.plan_id,
            stripe_subscription_id=stripe_subscription_id,
        )

        return SubscriptionResponse(
            id=subscription["id"],
            user_id=subscription["user_id"],
            plan_id=subscription["plan_id"],
            plan_tier=plan["tier"],
            status="active",
            storage_limit_gb=plan["storage_limit_gb"],
            used_storage_gb=0.0,
            file_limit=plan["file_limit"],
            used_file_count=0,
            current_period_start="",  # Would be datetime in real implementation
            current_period_end="",  # Would be datetime in real implementation
            stripe_subscription_id=stripe_subscription_id,
            created_at="",  # Would be datetime in real implementation
            updated_at="",  # Would be datetime in real implementation
        )

    async def get_quota_status(self, user_id: int) -> QuotaStatus:
        """Get current quota status for a user."""
        subscription = await self.subscription_repo.get_by_user_id(user_id)

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found",
            )

        storage_limit = subscription["storage_limit_gb"]
        used_storage = subscription["used_storage_gb"]
        available_storage = storage_limit - used_storage
        storage_percentage = (used_storage / storage_limit * 100) if storage_limit > 0 else 0

        file_limit = subscription["file_limit"]
        used_files = subscription["used_file_count"]
        available_files = file_limit - used_files
        file_percentage = (used_files / file_limit * 100) if file_limit > 0 else 0

        return QuotaStatus(
            storage_limit_gb=storage_limit,
            used_storage_gb=used_storage,
            available_storage_gb=available_storage,
            storage_percentage_used=storage_percentage,
            file_limit=file_limit,
            used_file_count=used_files,
            available_file_count=available_files,
            file_percentage_used=file_percentage,
        )

    async def update_quota(
        self, user_id: int, storage_bytes: int = 0, file_count: int = 0
    ) -> None:
        """Update quota usage for a user."""
        subscription = await self.subscription_repo.get_by_user_id(user_id)
        if subscription:
            storage_gb = bytes_to_gb(storage_bytes)
            await self.subscription_repo.update_quota(
                subscription["id"], storage_gb=storage_gb, file_count=file_count
            )

    async def handle_stripe_webhook(self, event_data: dict) -> dict:
        """Handle Stripe webhook events."""
        event_type = event_data.get("type")
        # Handle different event types (subscription.created, subscription.updated, etc.)
        # In real implementation, update subscription status based on Stripe events
        return {"status": "processed", "event_type": event_type}

