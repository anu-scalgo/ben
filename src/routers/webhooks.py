"""Webhook routes for external services (Stripe, etc.)."""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from ..config.database import get_db
from ..config import settings
from ..services.subscription_service import SubscriptionService
from ..config.stripe import stripe_client
from ..schemas.shared import SuccessResponse

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe", response_model=SuccessResponse)
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Stripe webhook events.
    Verifies webhook signature and processes events.
    """
    payload = await request.body()

    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature",
        )

    try:
        # Verify webhook signature
        event = stripe_client.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload: {str(e)}",
        )
    except stripe_client.error.SignatureVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid signature: {str(e)}",
        )

    # Process webhook event
    subscription_service = SubscriptionService(db)
    result = await subscription_service.handle_stripe_webhook(event)

    return SuccessResponse(
        message="Webhook processed successfully",
        data=result,
    )

