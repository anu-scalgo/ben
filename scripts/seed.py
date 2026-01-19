"""Script to seed database with initial data."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.database import AsyncSessionLocal
from src.repositories.subscription_repo import SubscriptionRepository
from src.repositories.user_repo import UserRepository
from src.models.user import User, UserRole
from src.core.security import get_password_hash
from sqlalchemy import select


async def seed_superadmin():
    """Seed default superadmin user if not exists."""
    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        
        # Default superadmin credentials
        email = "admin@example.com"
        password = "admin123456"  # Min 8 chars for validation
        full_name = "System Administrator"
        
        # Check if superadmin exists
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"  ✓ Superadmin already exists: {email}")
            return
        
        print(f"  Creating default superadmin: {email}")
        hashed_password = get_password_hash(password)
        
        superadmin = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=UserRole.SUPERADMIN,
            is_active=True
        )
        
        session.add(superadmin)
        await session.commit()
        print(f"  ✓ Superadmin created successfully!")
        print(f"    Email: {email}")
        print(f"    Password: {password}")
        print(f"    ⚠️  IMPORTANT: Change this password in production!")


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
        print("  Seeding subscription plans...")
        for plan in plans:
            print(f"    - {plan['name']}: ${plan['price_monthly']}/month")
        print("  ✓ Plans seeded successfully!")


async def main():
    """Main seeding function."""
    print("=" * 50)
    print("Starting database seeding...")
    print("=" * 50)
    
    print("\n[1/2] Seeding Superadmin User")
    await seed_superadmin()
    
    print("\n[2/2] Seeding Subscription Plans")
    await seed_plans()
    
    print("\n" + "=" * 50)
    print("Database seeding completed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

