
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.database import AsyncSessionLocal
from src.repositories.user_repo import UserRepository
from src.core.security import get_password_hash
from src.models.user import User
from sqlalchemy import select, update

async def reset_password():
    async with AsyncSessionLocal() as session:
        email = "admin@example.com"
        new_password = "admin123456"
        hashed_password = get_password_hash(new_password)
        
        print(f"Resetting password for {email}...")
        
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            user.hashed_password = hashed_password
            session.add(user)
            await session.commit()
            print("Password reset successfully.")
        else:
            print("User not found.")

if __name__ == "__main__":
    asyncio.run(reset_password())
