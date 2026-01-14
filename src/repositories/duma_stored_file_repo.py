"""DumaStoredFile repository."""

from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from .base import BaseRepository
from ..models.duma_stored_file import DumaStoredFile

class DumaStoredFileRepository(BaseRepository):
    """Repository for DumaStoredFile operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_file_record(
        self,
        dumapod_id: int,
        user_id: int,
        file_name: str,
        file_type: str,
        file_size: int,
        s3_url: Optional[str] = None,
        wasabi_url: Optional[str] = None,
        oracle_url: Optional[str] = None,
    ) -> DumaStoredFile:
        """Create a new file record."""
        file_record = DumaStoredFile(
            dumapod_id=dumapod_id,
            user_id=user_id,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            s3_url=s3_url,
            wasabi_url=wasabi_url,
            oracle_url=oracle_url,
        )
        self.session.add(file_record)
        await self.session.commit()
        await self.session.refresh(file_record)
        return file_record

    async def get_total_usage(self, dumapod_id: int) -> int:
        """Get total storage usage for a DumaPod in bytes."""
        stmt = select(func.sum(DumaStoredFile.file_size)).where(
            DumaStoredFile.dumapod_id == dumapod_id
        )
        result = await self.session.execute(stmt)
        total_size = result.scalar()
        return total_size or 0
