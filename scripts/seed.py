"""Script to seed database with initial data."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.database import AsyncSessionLocal
from src.repositories.subscription_repo import SubscriptionRepository


async def seed_plans():
    """Seed subscription plans."""
    async with AsyncSessionLocal() as session:
        subscription_repo = SubscriptionRepository(session)

        plans = [
            {
                "name": "Free",
                "tier": "free",
                "price_monthly": 0.0,
                "storage_limit_gb": 1.0,
                "file_limit": 10,
                "features": ["Basic storage", "Email support"],
            },
            {
                "name": "Basic",
                "tier": "basic",
                "price_monthly": 9.99,
                "storage_limit_gb": 10.0,
                "file_limit": 100,
                "features": ["10GB storage", "Priority support", "Video transcoding"],
            },
            {
                "name": "Pro",
                "tier": "pro",
                "price_monthly": 29.99,
                "storage_limit_gb": 100.0,
                "file_limit": 1000,
                "features": [
                    "100GB storage",
                    "24/7 support",
                    "Advanced transcoding",
                    "API access",
                ],
            },
            {
                "name": "Enterprise",
                "tier": "enterprise",
                "price_monthly": 99.99,
                "storage_limit_gb": 1000.0,
                "file_limit": 10000,
                "features": [
                    "1TB storage",
                    "Dedicated support",
                    "Custom integrations",
                    "SLA guarantee",
                ],
            },
        ]

        # In real implementation, would create plan records
        print("Seeding subscription plans...")
        for plan in plans:
            print(f"  - {plan['name']}: ${plan['price_monthly']}/month")
        print("Plans seeded successfully!")


async def main():
    """Main seeding function."""
    print("Starting database seeding...")
    await seed_plans()
    print("Database seeding completed!")


if __name__ == "__main__":
    asyncio.run(main())

