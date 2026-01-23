"""Multipart upload schemas - add to file.py"""

from typing import List, Optional
from pydantic import BaseModel, Field


class MultipartPartInfo(BaseModel):
    """Information about a single part in multipart upload."""
    part_number: int = Field(..., description="Part number (1-indexed)")
    upload_url: str = Field(..., description="Presigned URL for uploading this part")
    size: Optional[int] = Field(None, description="Expected size of this part in bytes")


class InitiateMultipartUploadRequest(BaseModel):
    """Request to initiate multipart upload."""
    dumapod_id: int = Field(..., description="ID of the DumaPod to upload to")
    filename: str = Field(..., description="Name of the file")
    content_type: str = Field(..., description="MIME type of the file")
    file_size: int = Field(..., gt=0, description="Total file size in bytes")
    part_size: Optional[int] = Field(None, description="Size of each part in bytes (optional, will be calculated if not provided)")
    description: Optional[str] = Field(None, description="Optional file description")


class InitiateMultipartUploadResponse(BaseModel):
    """Response from initiating multipart upload."""
    file_id: int = Field(..., description="Database ID of the file record")
    upload_id: str = Field(..., description="AWS multipart upload ID")
    storage_key: str = Field(..., description="S3 storage key/path")
    parts: List[MultipartPartInfo] = Field(..., description="List of parts with presigned URLs")
    total_parts: int = Field(..., description="Total number of parts")
    part_size: int = Field(..., description="Size of each part in bytes")
    expires_in: int = Field(..., description="URL expiration time in seconds")
    storage_provider: str = Field(..., description="Storage provider being used")


class MultipartPartComplete(BaseModel):
    """Information about a completed part."""
    part_number: int = Field(..., description="Part number (1-indexed)")
    etag: str = Field(..., description="ETag returned by S3 after uploading the part")


class CompleteMultipartUploadRequest(BaseModel):
    """Request to complete multipart upload."""
    upload_id: str = Field(..., description="AWS multipart upload ID")
    parts: List[MultipartPartComplete] = Field(..., description="List of completed parts with ETags")


class AbortMultipartUploadRequest(BaseModel):
    """Request to abort multipart upload."""
    upload_id: str = Field(..., description="AWS multipart upload ID")
