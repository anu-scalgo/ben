"""User repository for user data access."""

from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .base import BaseRepository
from ..models.user import User, UserRole


class UserRepository(BaseRepository):
    """Repository for user operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(
        self,
        email: str,
        hashed_password: str,
        full_name: str,
        role: UserRole = UserRole.ENDUSER,
    ) -> User:
        """Create a new user."""
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role,
            is_active=True,
        )
        self.session.add(user)
        result = await self.session.commit()
        return user

    async def get_by_id(self, id: int) -> Optional[User]:
        """Get user by ID."""
        stmt = select(User).where(User.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_user(self, user: User, data: Dict[str, Any]) -> User:
        """Update user attributes."""
        for key, value in data.items():
            setattr(user, key, value)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users."""
        stmt = select(User).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

