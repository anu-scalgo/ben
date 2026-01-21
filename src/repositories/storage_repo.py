"""Storage repository for multi-provider storage operations."""

import asyncio
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

    async def check_connectivity(self, provider: str, credentials: Optional[object] = None) -> bool:
        """
        Check connectivity to storage provider.
        """
        try:
            client = await self._get_client(provider, credentials)
            bucket = await self._get_bucket(provider, credentials)
            # Perform a lightweight operation to verify access, e.g., head_bucket or list_objects(max_keys=1)
            # head_bucket is strict on permissions, list might be better or head.
            # boto3 head_bucket: 
            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/head_bucket.html
            client.head_bucket(Bucket=bucket)
            return True
        except Exception as e:
            # Log error?
            return False

    async def upload_file(
        self, 
        file_content: bytes, 
        key: str, 
        content_type: str, 
        provider: Optional[str] = None, 
        credentials: Optional[object] = None,
        progress_callback: Optional[callable] = None
    ) -> str:
        """
        Upload file to storage.
        """
        client = await self._get_client(provider, credentials)
        bucket = await self._get_bucket(provider, credentials)
        
        loop = asyncio.get_running_loop()
        
        # Create a file-like object from bytes
        import io
        # Create a file-like object from bytes
        import io
        file_obj = io.BytesIO(file_content)
        
        def _upload():
            client.upload_fileobj(
                Fileobj=file_obj,
                Bucket=bucket,
                Key=key,
                ExtraArgs={'ContentType': content_type},
                Callback=progress_callback
            )
            
        await loop.run_in_executor(None, _upload)
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

    async def generate_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        file_size: int,
        expiration: int = 3600,
        provider: Optional[str] = None,
        credentials: Optional[object] = None
    ) -> dict:
        """
        Generate presigned URL for direct file upload.
        
        Args:
            key: Storage key (path) for the file
            content_type: MIME type of the file
            file_size: Size of the file in bytes
            expiration: URL expiration time in seconds (default: 1 hour)
            provider: Storage provider (s3, wasabi, oracle_object_storage)
            credentials: Optional custom credentials
            
        Returns:
            Dictionary with:
            - upload_url: Presigned URL for PUT upload
            - method: HTTP method (always "PUT")
            - headers: Required headers for the upload
        """
        client = await self._get_client(provider, credentials)
        bucket = await self._get_bucket(provider, credentials)
        
        try:
            # Generate presigned URL for PUT upload
            url = client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": bucket,
                    "Key": key,
                    "ContentType": content_type,
                    "ContentLength": file_size,
                },
                ExpiresIn=expiration,
            )
            
            return {
                "upload_url": url,
                "method": "PUT",
                "headers": {
                    "Content-Type": content_type,
                    "Content-Length": str(file_size),
                }
            }
        except ClientError as e:
            raise ValueError(f"Failed to generate presigned upload URL: {e}")

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

