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

