from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ..models.credential import StorageCredential
from ..schemas.credential import CredentialCreate, CredentialUpdate
from ..repositories.credential_repo import CredentialRepository
from ..models.dumapod import DumaPod


class CredentialService:
    """Service for managing storage credentials."""

    def __init__(self, db: AsyncSession):
        self.repo = CredentialRepository(db)
        self.db = db

    async def create_credential(self, dumapod_id: int, credential_data: CredentialCreate) -> StorageCredential:
        """Create a new credential for a DumaPod."""
        # Check if credential already exists for this provider
        existing = await self.repo.get_by_dumapod_and_provider(dumapod_id, credential_data.provider)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Credential for provider {credential_data.provider} already exists for this DumaPod."
            )

        credential = StorageCredential(
            dumapod_id=dumapod_id,
            **credential_data.model_dump()
        )
        return await self.repo.create(credential)

    async def get_credentials(self, dumapod_id: int) -> List[StorageCredential]:
        """Get all credentials for a DumaPod."""
        return await self.repo.get_by_dumapod_id(dumapod_id)

    async def update_credential(self, credential_id: int, update_data: CredentialUpdate) -> StorageCredential:
        """Update a credential."""
        credential = await self.repo.get_by_id(credential_id)
        if not credential:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
        
        return await self.repo.update(credential, update_data)

    async def delete_credential(self, credential_id: int) -> None:
        """Delete a credential."""
        credential = await self.repo.get_by_id(credential_id)
        if not credential:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
        
        await self.repo.delete(credential)
