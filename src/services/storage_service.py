"""Storage service for multi-provider storage operations."""

from typing import Optional
from ..repositories.storage_repo import StorageRepository
from ..config.storage import get_storage_client, get_bucket_name


class StorageService:
    """Service for storage operations."""

    def __init__(self):
        self.storage_repo = StorageRepository()

    async def upload_file(
        self, file_content: bytes, key: str, content_type: str, provider: Optional[str] = None
    ) -> str:
        """Upload file to storage."""
        return await self.storage_repo.upload_file(
            file_content=file_content, key=key, content_type=content_type, provider=provider
        )

    async def generate_presigned_url(
        self, key: str, expiration: int = 3600, provider: Optional[str] = None
    ) -> str:
        """Generate presigned URL for file access."""
        return await self.storage_repo.generate_presigned_url(
            key=key, expiration=expiration, provider=provider
        )

    async def delete_file(self, key: str, provider: Optional[str] = None) -> bool:
        """Delete file from storage."""
        return await self.storage_repo.delete_file(key, provider=provider)

    async def file_exists(self, key: str, provider: Optional[str] = None) -> bool:
        """Check if file exists in storage."""
        return await self.storage_repo.file_exists(key, provider=provider)

    def generate_key(self, user_id: int, filename: str, prefix: Optional[str] = None) -> str:
        """Generate storage key for file."""
        return self.storage_repo.generate_key(user_id, filename, prefix)

