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

    async def _calculate_connection_status(self, pod: DumaPod = None, pod_data: DumaPodCreate | DumaPodUpdate = None) -> dict[str, bool]:
        """Calculate connection status for a pod configuration."""
        status_map = {}
        from ..repositories.storage_repo import StorageRepository
        storage_repo = StorageRepository()
        
        # Helper to get attribute from object or dict
        def get_attr(obj, attr, default=None):
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(attr, default)
            return getattr(obj, attr, default)

        # Determine effective config
        # For pod_data (Create/Update), we use it if present and not None. Fallback to pod (existing).
        
        def get_effective_val(attr_name, default_val=False):
            val = get_attr(pod_data, attr_name)
            if val is not None:
                return val
            return get_attr(pod, attr_name, default_val)

        enable_s3 = get_effective_val('enable_s3')
        use_custom_s3 = get_effective_val('use_custom_s3')
        
        enable_wasabi = get_effective_val('enable_wasabi')
        use_custom_wasabi = get_effective_val('use_custom_wasabi')
        
        enable_oracle = get_effective_val('enable_oracle_os')
        use_custom_oracle = get_effective_val('use_custom_oracle')

        async def check(provider, is_custom):
            if is_custom:
                # For custom credentials, we need to access credentials list
                # Use pod object primarily if available
                # If pod is dict, credentials might be loaded? repo.get_all loads them.
                creds_list = []
                if pod:
                    if isinstance(pod, dict):
                         creds_list = pod.get('credentials', [])
                    else:
                         creds_list = getattr(pod, 'credentials', [])
                
                if creds_list:
                    # Filter for provider
                    cred = next((c for c in creds_list if (isinstance(c, dict) and c.get('provider') == provider) or (hasattr(c, 'provider') and c.provider == provider)), None)
                    if cred:
                        return await storage_repo.check_connectivity(provider, cred)
                return False 
            else:
                 return await storage_repo.check_connectivity(provider)

        if enable_s3:
            status_map[StorageProvider.AWS_S3] = await check(StorageProvider.AWS_S3, use_custom_s3)
        if enable_wasabi:
            status_map[StorageProvider.WASABI] = await check(StorageProvider.WASABI, use_custom_wasabi)
        if enable_oracle:
            status_map[StorageProvider.ORACLE_OS] = await check(StorageProvider.ORACLE_OS, use_custom_oracle)
            
        return status_map

    async def create_dumapod(self, pod_data: DumaPodCreate, user_id: int) -> DumaPod:
        """Create a new DumaPod."""
        
        self._validate_storage_config(
            pod_data.primary_storage, 
            pod_data.secondary_storage,
            pod_data.enable_s3,
            pod_data.enable_wasabi,
            pod_data.enable_oracle_os
        )
        
        # Check for existing pod with same name
        existing_pod = await self.repo.get_by_name(pod_data.name)
        if existing_pod:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"DumaPod with name '{pod_data.name}' already exists."
            )
        
        # Calculate initial status
        conn_status = await self._calculate_connection_status(pod_data=pod_data)

        return await self.repo.create(
            **pod_data.model_dump(),
            created_by=user_id,
            connection_status=conn_status
        )

    async def get_dumapod(self, pod_id: int) -> DumaPod:
        """Get DumaPod by ID."""
        pod = await self.repo.get_by_id(pod_id)
        if not pod:
            raise HTTPException(status_code=404, detail="DumaPod not found")
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

        updated_pod = await self.repo.update(pod_id, **pod_data.model_dump(exclude_unset=True))
        
        new_status = await self._calculate_connection_status(pod=updated_pod)
        
        if new_status != updated_pod.connection_status:
             updated_pod = await self.repo.update(pod_id, connection_status=new_status)

        return updated_pod

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

    async def check_and_update_connection_status(self, pod_id: int) -> dict[str, bool]:
        """Check and update connection status for a pod."""
        pod = await self.get_dumapod(pod_id)
        
        # Calculate new status based on current pod config
        new_status = await self._calculate_connection_status(pod=pod)
        
        # Update if changed
        if new_status != pod.connection_status:
             pod = await self.repo.update(pod_id, connection_status=new_status)
             
        return pod.connection_status
