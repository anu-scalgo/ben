"""Storage repository for multi-provider storage operations."""

import asyncio
from typing import Optional
import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError
from botocore.config import Config
from ..config.storage import get_storage_client, get_bucket_name
from ..config import settings
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

"""Multipart upload methods for storage repository."""

from typing import List, Dict, Optional
import math


# Add these methods to the StorageRepository class in storage_repo.py

async def initiate_multipart_upload(
    self,
    key: str,
    content_type: str,
    provider: Optional[str] = None,
    credentials: Optional[object] = None
) -> str:
    """
    Initiate multipart upload.
    
    Returns:
        upload_id: AWS multipart upload ID
    """
    client = await self._get_client(provider, credentials)
    bucket = await self._get_bucket(provider, credentials)
    
    try:
        response = client.create_multipart_upload(
            Bucket=bucket,
            Key=key,
            ContentType=content_type
        )
        return response['UploadId']
    except ClientError as e:
        raise Exception(f"Failed to initiate multipart upload: {str(e)}")


async def generate_multipart_presigned_urls(
    self,
    key: str,
    upload_id: str,
    total_parts: int,
    expiration: int = 3600,
    provider: Optional[str] = None,
    credentials: Optional[object] = None
) -> List[Dict]:
    """
    Generate presigned URLs for each part.
    
    Returns:
        List of dicts with part_number and upload_url
    """
    client = await self._get_client(provider, credentials)
    bucket = await self._get_bucket(provider, credentials)
    
    parts = []
    for part_number in range(1, total_parts + 1):
        url = client.generate_presigned_url(
            'upload_part',
            Params={
                'Bucket': bucket,
                'Key': key,
                'UploadId': upload_id,
                'PartNumber': part_number
            },
            ExpiresIn=expiration
        )
        parts.append({
            'part_number': part_number,
            'upload_url': url
        })
    
    return parts


async def complete_multipart_upload(
    self,
    key: str,
    upload_id: str,
    parts: List[Dict],  # [{"part_number": 1, "etag": "..."}]
    provider: Optional[str] = None,
    credentials: Optional[object] = None
) -> None:
    """Complete multipart upload by combining all parts."""
    client = await self._get_client(provider, credentials)
    bucket = await self._get_bucket(provider, credentials)
    
    # Format parts for S3
    multipart_upload = {
        'Parts': [
            {
                'PartNumber': part['part_number'],
                'ETag': part['etag']
            }
            for part in sorted(parts, key=lambda x: x['part_number'])
        ]
    }
    
    try:
        client.complete_multipart_upload(
            Bucket=bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload=multipart_upload
        )
    except ClientError as e:
        raise Exception(f"Failed to complete multipart upload: {str(e)}")


async def abort_multipart_upload(
    self,
    key: str,
    upload_id: str,
    provider: Optional[str] = None,
    credentials: Optional[object] = None
) -> None:
    """Abort multipart upload and clean up parts."""
    client = await self._get_client(provider, credentials)
    bucket = await self._get_bucket(provider, credentials)
    
    try:
        client.abort_multipart_upload(
            Bucket=bucket,
            Key=key,
            UploadId=upload_id
        )
    except ClientError as e:
        # Log but don't fail - cleanup is best effort
        print(f"Warning: Failed to abort multipart upload: {str(e)}")


def calculate_part_size(file_size: int, max_parts: int = 10000) -> tuple:
    """
    Calculate optimal part size for multipart upload.
    
    Returns:
        (part_size, total_parts)
    """
    # S3 limits
    MIN_PART_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_PART_SIZE = 5 * 1024 * 1024 * 1024  # 5GB
    
    # Recommended part sizes based on file size
    if file_size < 100 * 1024 * 1024:  # < 100MB
        part_size = 10 * 1024 * 1024  # 10MB
    elif file_size < 1 * 1024 * 1024 * 1024:  # < 1GB
        part_size = 100 * 1024 * 1024  # 100MB
    elif file_size < 10 * 1024 * 1024 * 1024:  # < 10GB
        part_size = 500 * 1024 * 1024  # 500MB
    else:
        part_size = 1 * 1024 * 1024 * 1024  # 1GB
    
    # Ensure part size is within limits
    part_size = max(MIN_PART_SIZE, min(part_size, MAX_PART_SIZE))
    
    # Calculate total parts
    total_parts = math.ceil(file_size / part_size)
    
    # If too many parts, increase part size
    if total_parts > max_parts:
        part_size = math.ceil(file_size / max_parts)
        total_parts = max_parts
    
    return (part_size, total_parts)
