import asyncio
import sys
import os

# Ensure src is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.models.user import User, UserRole
from src.core.security import get_password_hash
from src.config.database import AsyncSessionLocal
from sqlalchemy import select

async def create_superadmin():
    email = input("Enter Superadmin Email (default: superadmin@example.com): ").strip() or "superadmin@example.com"
    full_name = input("Enter Full Name (default: Super Admin): ").strip() or "Super Admin"
    password = input("Enter Password (default: secret123): ").strip() or "secret123"

    async with AsyncSessionLocal() as session:
        # Check if user exists
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"User with email {email} already exists.")
            return

        print(f"Creating superadmin: {email}")
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
        print("Superadmin created successfully!")

if __name__ == "__main__":
    try:
        asyncio.run(create_superadmin())
    except KeyboardInterrupt:
        print("\nAborted.")
