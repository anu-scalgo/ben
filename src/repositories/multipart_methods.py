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
