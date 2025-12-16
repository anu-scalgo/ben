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
        self.client: Optional[BaseClient] = None
        self.bucket_name: Optional[str] = None

    async def _get_client(self) -> BaseClient:
        """Get or create storage client."""
        if self.client is None:
            self.client = get_storage_client()
            self.bucket_name = get_bucket_name()
        return self.client

    async def upload_file(
        self, file_content: bytes, key: str, content_type: str
    ) -> str:
        """
        Upload file to storage.
        Args:
            file_content: File content as bytes
            key: Storage key (path)
            content_type: MIME type
        Returns:
            Storage key
        """
        client = await self._get_client()
        client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=file_content,
            ContentType=content_type,
        )
        return key

    async def generate_presigned_url(
        self, key: str, expiration: int = 3600
    ) -> str:
        """
        Generate presigned URL for file download.
        Args:
            key: Storage key
            expiration: URL expiration time in seconds
        Returns:
            Presigned URL
        """
        client = await self._get_client()
        try:
            url = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            raise ValueError(f"Failed to generate presigned URL: {e}")

    async def delete_file(self, key: str) -> bool:
        """
        Delete file from storage.
        Args:
            key: Storage key
        Returns:
            True if successful
        """
        client = await self._get_client()
        try:
            client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    async def file_exists(self, key: str) -> bool:
        """Check if file exists in storage."""
        client = await self._get_client()
        try:
            client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def generate_key(self, user_id: int, filename: str, prefix: Optional[str] = None) -> str:
        """Generate storage key for file."""
        return generate_s3_key(user_id, filename, prefix)

