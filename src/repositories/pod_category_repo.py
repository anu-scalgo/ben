"""Pod Category repository."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from .base import BaseRepository
from ..models.pod_category import PodCategory


class PodCategoryRepository(BaseRepository[PodCategory]):
    """Repository for Pod Category operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository."""
        super().__init__(session, PodCategory)

    async def get_by_name(self, name: str) -> PodCategory | None:
        """Get category by name."""
        result = await self.session.execute(
            select(PodCategory).where(PodCategory.name == name)
        )
        return result.scalar_one_or_none()
