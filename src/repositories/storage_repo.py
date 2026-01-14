"""Storage repository for multi-provider storage operations."""

from typing import Optional
import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError
from ..config.storage import get_storage_client, get_bucket_name
from ..utils.helpers import generate_s3_key


class StorageRepository:
    """Repository for storage operations across multiple providers."""

    def __init__(self):
        # Cache clients by provider name
        self.clients: dict[str, BaseClient] = {}
        self.buckets: dict[str, str] = {}

    async def _get_client(self, provider: Optional[str] = None, credentials: Optional[object] = None) -> BaseClient:
        """
        Get or create storage client.
        If credentials provided, creates a new client.
        """
        if credentials:
            # Create transient client for custom credentials
            return boto3.client(
                "s3",
                aws_access_key_id=credentials.access_key,
                aws_secret_access_key=credentials.secret_key,
                region_name=credentials.region or settings.aws_region,
                endpoint_url=credentials.endpoint_url,
                config=Config(signature_version="s3v4"),
            )

        if not provider:
            provider = settings.storage_provider
        
        provider = provider.lower()

        if provider not in self.clients:
            self.clients[provider] = get_storage_client(provider)
            self.buckets[provider] = get_bucket_name(provider)
            
        return self.clients[provider]

    async def _get_bucket(self, provider: Optional[str] = None, credentials: Optional[object] = None) -> str:
        """Get bucket name."""
        if credentials:
            return credentials.bucket_name

        if not provider:
            provider = settings.storage_provider
        
        provider = provider.lower()
        
        if provider not in self.buckets:
            await self._get_client(provider)
            
        return self.buckets[provider]

    async def upload_file(
        self, file_content: bytes, key: str, content_type: str, provider: Optional[str] = None, credentials: Optional[object] = None
    ) -> str:
        """
        Upload file to storage.
        """
        client = await self._get_client(provider, credentials)
        bucket = await self._get_bucket(provider, credentials)
        
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=file_content,
            ContentType=content_type,
        )
        return key

    async def generate_presigned_url(
        self, key: str, expiration: int = 3600, provider: Optional[str] = None
    ) -> str:
        """
        Generate presigned URL for file download.
        Args:
            key: Storage key
            expiration: URL expiration time in seconds
            provider: Storage provider
        Returns:
            Presigned URL
        """
        client = await self._get_client(provider)
        bucket = await self._get_bucket(provider)
        
        try:
            url = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            raise ValueError(f"Failed to generate presigned URL: {e}")

    async def delete_file(self, key: str, provider: Optional[str] = None) -> bool:
        """
        Delete file from storage.
        Args:
            key: Storage key
            provider: Storage provider
        Returns:
            True if successful
        """
        client = await self._get_client(provider)
        bucket = await self._get_bucket(provider)
        
        try:
            client.delete_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False

    async def file_exists(self, key: str, provider: Optional[str] = None) -> bool:
        """Check if file exists in storage."""
        client = await self._get_client(provider)
        bucket = await self._get_bucket(provider)
        
        try:
            client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False

    def generate_key(self, user_id: int, filename: str, prefix: Optional[str] = None) -> str:
        """Generate storage key for file."""
        return generate_s3_key(user_id, filename, prefix)

