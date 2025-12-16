"""Base repository with common database operations."""

from typing import Generic, TypeVar, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""

    def __init__(self, session: AsyncSession, model: type[ModelType]):
        """
        Initialize repository.
        Args:
            session: Async database session
            model: SQLAlchemy model class
        """
        self.session = session
        self.model = model

    async def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Get entity by ID."""
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        entity = result.scalar_one_or_none()
        return self._to_dict(entity) if entity else None

    async def get_all(
        self, skip: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all entities with pagination."""
        result = await self.session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        entities = result.scalars().all()
        return [self._to_dict(e) for e in entities]

    async def create(self, **kwargs) -> Dict[str, Any]:
        """Create new entity."""
        entity = self.model(**kwargs)
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return self._to_dict(entity)

    async def update(self, id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Update entity by ID."""
        await self.session.execute(
            update(self.model).where(self.model.id == id).values(**kwargs)
        )
        await self.session.flush()
        return await self.get_by_id(id)

    async def delete(self, id: int) -> bool:
        """Delete entity by ID."""
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.session.flush()
        return result.rowcount > 0

    def _to_dict(self, entity: Optional[ModelType]) -> Optional[Dict[str, Any]]:
        """Convert SQLAlchemy model to dictionary."""
        if entity is None:
            return None
        return {
            column.name: getattr(entity, column.name)
            for column in entity.__table__.columns
        }

