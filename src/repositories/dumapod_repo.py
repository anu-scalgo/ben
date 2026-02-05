"""DumaPod repository."""

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from .base import BaseRepository
from ..models.dumapod import DumaPod


class DumaPodRepository(BaseRepository[DumaPod]):
    """Repository for DumaPod operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, DumaPod)

    async def get_by_name(self, name: str) -> DumaPod | None:
        """Get DumaPod by name."""
        from sqlalchemy import select
        stmt = select(DumaPod).where(DumaPod.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        """Get all DumaPods sorted by creation date (newest first)."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        stmt = (
            select(DumaPod)
            .options(selectinload(DumaPod.credentials))
            .order_by(DumaPod.created_at.desc())
            .offset(skip).limit(limit)
        )
        result = await self.session.execute(stmt)
        # return entities directly or handle conversion in service?
        # Standard repository returns dicts.
        # But for connection status, we need the relationships.
        # BaseRepository._to_dict usually doesn't include relationships unless we modify it or handle it.
        # Wait, if we return dicts, we lose the credentials unless we check _to_dict implementation.
        # _to_dict only iterates columns.
        
        # We need to return the model instances to the service OR manually attach credentials to the dict.
        # Service needs to calculate connection status.
        # Let's return Model instances from repository and let Service handle conversion to response model (which Pydantic does easily fromORM).
        # But BaseRepository contract says Dict.
        
        # Let's override behavior here to return objects or enhanced dicts.
        # Simpler: Return list of DumaPod objects. Service can process them.
        return result.scalars().all()
