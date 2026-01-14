"""DumaPod repository."""

from sqlalchemy.ext.asyncio import AsyncSession
from .base import BaseRepository
from ..models.dumapod import DumaPod


class DumaPodRepository(BaseRepository[DumaPod]):
    """Repository for DumaPod operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, DumaPod)

    # BaseRepository covers basic CRUD: create, get_by_id, get_all, update, delete
    # Add specific methods if needed, e.g. get_by_name if we enforce unique names
