"""DumaPod service."""

from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..repositories.dumapod_repo import DumaPodRepository
from ..models.dumapod import DumaPod, StorageProvider
from ..schemas.dumapod import DumaPodCreate, DumaPodUpdate


class DumaPodService:
    """Service for DumaPod operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DumaPodRepository(db)

    def _validate_storage_config(self, primary: StorageProvider, secondary: Optional[StorageProvider], enable_s3: bool, enable_wasabi: bool, enable_oracle: bool):
        """Validate that selected storage providers are enabled."""
        
        # Check Primary
        if primary == StorageProvider.AWS_S3 and not enable_s3:
            raise HTTPException(status_code=400, detail="Amazon S3 must be enabled to be used as Primary Storage")
        if primary == StorageProvider.WASABI and not enable_wasabi:
            raise HTTPException(status_code=400, detail="Wasabi must be enabled to be used as Primary Storage")
        if primary == StorageProvider.ORACLE_OS and not enable_oracle:
            raise HTTPException(status_code=400, detail="Oracle Object Storage must be enabled to be used as Primary Storage")

        # Check Secondary
        if secondary:
            if secondary == primary:
                raise HTTPException(status_code=400, detail="Secondary storage cannot be the same as Primary storage")
                
            if secondary == StorageProvider.AWS_S3 and not enable_s3:
                raise HTTPException(status_code=400, detail="Amazon S3 must be enabled to be used as Secondary Storage")
            if secondary == StorageProvider.WASABI and not enable_wasabi:
                raise HTTPException(status_code=400, detail="Wasabi must be enabled to be used as Secondary Storage")
            if secondary == StorageProvider.ORACLE_OS and not enable_oracle:
                raise HTTPException(status_code=400, detail="Oracle Object Storage must be enabled to be used as Secondary Storage")

    async def create_dumapod(self, pod_data: DumaPodCreate, user_id: int) -> DumaPod:
        """Create a new DumaPod."""
        
        self._validate_storage_config(
            pod_data.primary_storage, 
            pod_data.secondary_storage,
            pod_data.enable_s3,
            pod_data.enable_wasabi,
            pod_data.enable_oracle_os
        )
        
        # Check unique namme? 
        # For now, let DB constraint handle it or catch integrity error in repo.
        # Ideally, check here.
        # We can implement get_by_name in repo later.
        
        return await self.repo.create(
            **pod_data.model_dump(),
            created_by=user_id
        )

    async def get_dumapod(self, pod_id: int) -> DumaPod:
        """Get DumaPod by ID."""
        pod = await self.repo.get_by_id(pod_id)
        if not pod:
            raise HTTPException(status_code=404, detail="DumaPod not found")
        # BaseRepository returns dict? No, I updated BaseRepository to return dicts in get_by_id but my Typed annotation said Optional[Dict].
        # Wait, BaseRepository methods return Dicts because of `_to_dict`.
        # Previous User implementation seemed to rely on User objects.
        # Let's check BaseRepository implementation again.
        return pod

    async def get_all_dumapods(self, skip: int = 0, limit: int = 100) -> List[DumaPod]:
        """Get all DumaPods."""
        return await self.repo.get_all(skip, limit)

    async def update_dumapod(self, pod_id: int, pod_data: DumaPodUpdate) -> DumaPod:
        """Update DumaPod."""
        # Check if enabling custom credentials
        if pod_data.use_custom_s3 is True:
            await self._validate_credential_connectivity(pod_id, StorageProvider.AWS_S3)
        if pod_data.use_custom_wasabi is True:
            await self._validate_credential_connectivity(pod_id, StorageProvider.WASABI)
        if pod_data.use_custom_oracle is True:
            await self._validate_credential_connectivity(pod_id, StorageProvider.ORACLE_OS)

        return await self.repo.update(pod_id, **pod_data.model_dump(exclude_unset=True))

    async def _validate_credential_connectivity(self, pod_id: int, provider: StorageProvider):
        """Helper to validate credential connectivity."""
        from ..repositories.credential_repo import CredentialRepository
        from ..repositories.storage_repo import StorageRepository
        
        cred_repo = CredentialRepository(self.db)
        credential = await cred_repo.get_by_dumapod_and_provider(pod_id, provider)
        
        if not credential:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot enable custom {provider}: No custom credentials found."
            )
            
        storage_repo = StorageRepository()
        is_connected = await storage_repo.check_connectivity(provider, credential)
        
        if not is_connected:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot enable custom {provider}: Connectivity check failed. Please check your credentials."
            )

    async def delete_dumapod(self, pod_id: int) -> bool:
        """Delete DumaPod."""
        # Use soft delete by setting active=False? Request said "crud apis" usually implies DELETE method.
        # Plan said Soft Delete or Hard.
        # Let's do hard delete for 'DELETE' method, or soft.
        # Implementation Plan said "Soft delete (set is_active=False)".
        
        return await self.repo.update(pod_id, is_active=False)
