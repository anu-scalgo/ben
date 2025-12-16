"""Reusable FastAPI dependencies."""

from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..config.database import get_db
from ..middleware.auth import get_current_user
from ..middleware.quota import check_quota, check_plan_tier
from ..repositories.user_repo import UserRepository
from ..repositories.subscription_repo import SubscriptionRepository
from ..repositories.file_repo import FileRepository
from ..repositories.storage_repo import StorageRepository


async def get_user_repo(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[UserRepository, None]:
    """Dependency to get user repository."""
    yield UserRepository(db)


async def get_subscription_repo(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[SubscriptionRepository, None]:
    """Dependency to get subscription repository."""
    yield SubscriptionRepository(db)


async def get_file_repo(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[FileRepository, None]:
    """Dependency to get file repository."""
    yield FileRepository(db)


async def get_storage_repo() -> AsyncGenerator[StorageRepository, None]:
    """Dependency to get storage repository."""
    yield StorageRepository()

