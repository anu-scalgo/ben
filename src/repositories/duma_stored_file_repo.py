"""DumaStoredFile repository."""

from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
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
        upload_status: str = "pending",
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
            upload_status=upload_status,
        )
        self.session.add(file_record)
        await self.session.commit()
        await self.session.refresh(file_record)
        return file_record

    async def get_total_usage(self, dumapod_id: int) -> int:
        """Get total storage usage for a DumaPod in bytes (excluding failed uploads)."""
        stmt = select(func.sum(DumaStoredFile.file_size)).where(
            DumaStoredFile.dumapod_id == dumapod_id,
            DumaStoredFile.upload_status != "failed"
        )
        result = await self.session.execute(stmt)
        total_size = result.scalar()
        return total_size or 0

    async def get_file_count(self, dumapod_id: int) -> int:
        """Get total file count for a DumaPod (excluding failed uploads)."""
        stmt = select(func.count()).select_from(DumaStoredFile).where(
            DumaStoredFile.dumapod_id == dumapod_id,
            DumaStoredFile.upload_status != "failed"
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_file(self, file_id: int) -> Optional[DumaStoredFile]:
        """Get file by ID."""
        stmt = select(DumaStoredFile).where(DumaStoredFile.id == file_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_file_status_and_urls(
        self,
        file_id: int,
        status: str,
        s3_url: Optional[str] = None,
        wasabi_url: Optional[str] = None,
        oracle_url: Optional[str] = None,
    ) -> Optional[DumaStoredFile]:
        """Update file status and URLs."""
        # Use direct update to avoid ORM session conflicts with progress tracking
        stmt = (
            text("UPDATE duma_stored_files SET upload_status = :status, s3_url = :s3, wasabi_url = :wasabi, oracle_url = :oracle WHERE id = :id")
            .bindparams(status=status, s3=s3_url, wasabi=wasabi_url, oracle=oracle_url, id=file_id)
        )
        # However, we only want to update URLs if provided?
        # The previous logic did: if s3_url: file_record.s3_url = s3_url
        # If I pas None to bindparams, it sets NULL in DB!
        # OLD logic: if s3_url is None, it keeps existing value.
        # SQL logic: COALESCE? Or dynamic query building.
        
        # Build dynamic query
        update_values = {"status": status}
        set_clauses = ["upload_status = :status"]
        
        if s3_url is not None:
            update_values["s3"] = s3_url
            set_clauses.append("s3_url = :s3")
        if wasabi_url is not None:
            update_values["wasabi"] = wasabi_url
            set_clauses.append("wasabi_url = :wasabi")
        if oracle_url is not None:
            update_values["oracle"] = oracle_url
            set_clauses.append("oracle_url = :oracle")
            
        final_stmt = text(f"UPDATE duma_stored_files SET {', '.join(set_clauses)} WHERE id = :id")
        final_stmt = final_stmt.bindparams(id=file_id, **update_values)
        
        await self.session.execute(final_stmt)
        await self.session.commit()
        
        # Fetch fresh object to return
        # First expire identity map to ensure fresh fetch
        # Since we used direct update, validation of cached object is tricky.
        # But we can just query.
        # Wait, if we fetch using get_file, and it's in session, we get stale.
        # We should expire it first?
        # But we don't have the object instance here easily unless we fetched it.
        # We can just rely on the fact that we return what we fetched?
        # Or fetch using populate_existing()?
        
        stmt = select(DumaStoredFile).where(DumaStoredFile.id == file_id).execution_options(populate_existing=True)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_upload_progress(self, file_id: int, progress: int) -> None:
        """Update upload progress percentage."""
        # Use execute for efficiency to avoid loading object if not needed, 
        # but fetching is fine. Let's fetch to be safe with ORM.
        # Actually, let's use a direct update statement for speed/concurrency 
        # although with asyncpg it's fast.
        stmt = (
            text("UPDATE duma_stored_files SET upload_progress = :progress WHERE id = :id")
            .bindparams(progress=progress, id=file_id)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_by_user_and_id(
        self, user_id: int, file_id: int
    ) -> Optional[DumaStoredFile]:
        """Get file by ID and user ID."""
        stmt = select(DumaStoredFile).where(
            DumaStoredFile.id == file_id,
            DumaStoredFile.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> list[DumaStoredFile]:
        """Get all files for a user with pagination."""
        stmt = (
            select(DumaStoredFile)
            .where(DumaStoredFile.user_id == user_id)
            .order_by(DumaStoredFile.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_file_count_by_user(self, user_id: int) -> int:
        """Get total file count for a user."""
        stmt = select(func.count()).select_from(DumaStoredFile).where(
            DumaStoredFile.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
