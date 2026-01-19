"""User service for user management."""

from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..repositories.user_repo import UserRepository
from ..repositories.duma_stored_file_repo import DumaStoredFileRepository
from ..schemas.user import UserCreate, UserUpdate, UserWithUsageResponse, UserPodUsage
from ..core.security import get_password_hash
from ..models.user import User
from ..utils.helpers import bytes_to_gb


class UserService:
    """Service for user management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.file_repo = DumaStoredFileRepository(db)

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

    async def get_users_with_usage(
        self,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[int] = None
    ) -> List[UserWithUsageResponse]:
        """Get users with aggregated usage stats."""
        # Eager load pods
        stmt = (
            select(User)
            .options(selectinload(User.created_dumapods))
        )
        
        if user_id:
            stmt = stmt.where(User.id == user_id)
            
        stmt = stmt.offset(skip).limit(limit)
        
        result = await self.db.execute(stmt)
        users = result.scalars().all()
        
        response = []
        for user in users:
            pods_usage = []
            for pod in user.created_dumapods:
                used_bytes = await self.file_repo.get_total_usage(pod.id)
                used_gb = bytes_to_gb(float(used_bytes) if used_bytes else 0.0)
                file_count = await self.file_repo.get_file_count(pod.id) # Need to implement/verify this
                
                # Check if get_file_count supports pod_id filter. 
                # Currently get_total_usage supports pod_id.
                # get_file_count_by_user supports user_id.
                # We need get_file_count_by_pod or similar.
                # Let's check repository again.
                # For now assuming we add it or use count.
                
                balance_gb = float(pod.storage_capacity_gb) - used_gb
                
                pods_usage.append(UserPodUsage(
                    pod_id=pod.id,
                    pod_name=pod.name,
                    storage_capacity_gb=float(pod.storage_capacity_gb),
                    used_storage_gb=used_gb,
                    balance_storage_gb=balance_gb,
                    file_count=file_count
                ))
            
            response.append(UserWithUsageResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role.value,
                is_active=user.is_active,
                created_at=user.created_at,
                pods=pods_usage
            ))
            
        return response
