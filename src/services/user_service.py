"""User service for user management."""

from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..repositories.user_repo import UserRepository
from ..schemas.user import UserCreate, UserUpdate
from ..core.security import get_password_hash
from ..models.user import User


class UserService:
    """Service for user management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def get_user(self, user_id: int) -> User:
        """Get user by ID."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user (admin function)."""
        existing_user = await self.user_repo.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        hashed_password = get_password_hash(user_data.password)
        return await self.user_repo.create_user(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            role=user_data.role,
        )

    async def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        """Update user details."""
        user = await self.get_user(user_id)
        
        data = user_data.model_dump(exclude_unset=True)
        if "password" in data:
            data["hashed_password"] = get_password_hash(data.pop("password"))
            
        return await self.user_repo.update_user(user, data)

    async def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users."""
        return await self.user_repo.get_all_users(skip, limit)
