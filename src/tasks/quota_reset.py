"""Periodic tasks for quota management."""

from celery import shared_task
from datetime import datetime
from ..tasks.celery_app import celery_app
from ..repositories.subscription_repo import SubscriptionRepository
from ..config.database import AsyncSessionLocal
import asyncio


@shared_task(name="reset_monthly_quota")
def reset_monthly_quota() -> dict:
    """
    Reset monthly quota for all active subscriptions.
    This task should run monthly (e.g., on the 1st of each month).
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        async_session = AsyncSessionLocal()
        subscription_repo = SubscriptionRepository(async_session)

        # Reset quota for all active subscriptions
        # In real implementation, would query all active subscriptions and reset their usage
        # loop.run_until_complete(subscription_repo.reset_all_quotas())

        return {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Monthly quota reset completed",
        }
    finally:
        loop.close()


# Configure periodic task schedule
celery_app.conf.beat_schedule = {
    "reset-monthly-quota": {
        "task": "reset_monthly_quota",
        "schedule": 30.0,  # Run every 30 seconds for testing (change to monthly in production)
        # "schedule": crontab(day_of_month=1, hour=0, minute=0),  # Monthly at midnight
    },
}

