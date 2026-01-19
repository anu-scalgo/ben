from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ..models.credential import StorageCredential
from ..schemas.credential import CredentialCreate, CredentialUpdate


class CredentialRepository:
    """Repository for StorageCredential operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, credential: StorageCredential) -> StorageCredential:
        """Create a new credential."""
        self.db.add(credential)
        await self.db.commit()
        await self.db.refresh(credential)
        return credential

    async def get_by_id(self, credential_id: int) -> Optional[StorageCredential]:
        """Get credential by ID."""
        query = select(StorageCredential).where(StorageCredential.id == credential_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_dumapod_id(self, dumapod_id: int) -> List[StorageCredential]:
        """Get all credentials for a DumaPod."""
        query = select(StorageCredential).where(StorageCredential.dumapod_id == dumapod_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_dumapod_and_provider(self, dumapod_id: int, provider: str) -> Optional[StorageCredential]:
        """Get credential by DumaPod ID and provider."""
        query = select(StorageCredential).where(
            StorageCredential.dumapod_id == dumapod_id,
            StorageCredential.provider == provider
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update(self, credential: StorageCredential, update_data: CredentialUpdate) -> StorageCredential:
        """Update a credential."""
        for key, value in update_data.model_dump(exclude_unset=True).items():
            setattr(credential, key, value)
        await self.db.commit()
        await self.db.refresh(credential)
        return credential

    async def delete(self, credential: StorageCredential) -> None:
        """Delete a credential."""
        await self.db.delete(credential)
        await self.db.commit()
