import asyncio
import sys
import os

sys.path.append(os.getcwd())

from src.models.user import User
from src.core.security import get_password_hash
from src.config.database import AsyncSessionLocal
from sqlalchemy import select

async def update_superadmin_password():
    email = "superadmin@example.com"
    new_password = "secret123"

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            print(f"User {email} not found.")
            return

        print(f"Updating password for: {email}")
        user.hashed_password = get_password_hash(new_password)
        session.add(user)
        await session.commit()
        print("Password updated successfully!")

if __name__ == "__main__":
    asyncio.run(update_superadmin_password())
