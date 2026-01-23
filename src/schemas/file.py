"""File upload and management schemas."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from ..middleware.validation import FileValidators


class FileUpload(BaseModel):
    """File upload metadata schema."""

    filename: str
    content_type: str = Field(..., description="MIME type of the file")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    description: Optional[str] = Field(None, max_length=500)

    # Apply validators
    _validate_file_size = FileValidators.validate_file_size_bytes
    _validate_content_type = FileValidators.validate_content_type


class FileResponse(BaseModel):
    """File response schema."""

    id: int
    user_id: int
    filename: str
    original_filename: str
    content_type: str
    file_size: int
    storage_key: str
    storage_provider: str
    description: Optional[str] = None
    transcoded_urls: List[str] = Field(
        default_factory=list, description="URLs to transcoded versions"
    )
    upload_status: str = Field(default="pending", description="pending, processing, completed, failed")
    upload_progress: int = Field(default=0, description="Upload progress percentage (0-100)")
    failed_reason: Optional[str] = Field(default=None, description="Error message if upload failed")
    
    s3_url: Optional[str] = None
    wasabi_url: Optional[str] = None
    oracle_url: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    """File list response with pagination."""

    files: List[FileResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class FileDownloadResponse(BaseModel):
    """File download response with presigned URL."""

    file_id: int
    filename: str
    download_url: str
    expires_in: int = Field(default=3600, description="URL expiration time in seconds")
    file_size: int
    content_type: str



class InitiateUploadRequest(BaseModel):
    """Request to initiate direct upload."""
    
    dumapod_id: int = Field(..., description="ID of the DumaPod to upload to")
    filename: str = Field(..., min_length=1, max_length=255, description="Original filename")
    content_type: str = Field(..., description="MIME type of the file")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    description: Optional[str] = Field(None, max_length=500, description="Optional file description")
    
    # Apply validators
    _validate_file_size = FileValidators.validate_file_size_bytes
    _validate_content_type = FileValidators.validate_content_type


class PresignedUploadResponse(BaseModel):
    """Response with presigned upload URL for direct S3 upload."""
    
    file_id: int = Field(..., description="Database ID of the file record")
    upload_url: str = Field(..., description="Presigned URL for uploading the file")
    upload_method: str = Field(default="PUT", description="HTTP method to use (PUT or POST)")
    upload_headers: dict = Field(default_factory=dict, description="Required headers for the upload")
    expires_in: int = Field(default=3600, description="URL expiration time in seconds")
    storage_key: str = Field(..., description="Storage key (path) where file will be stored")
    storage_provider: str = Field(..., description="Storage provider (s3, wasabi, oracle)")


class ConfirmUploadRequest(BaseModel):
    """Request to confirm upload completion (optional, can use empty POST)."""
    
    pass  # No fields needed, file_id comes from URL path
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
