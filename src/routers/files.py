"""File upload and management routes."""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from ..config.database import get_db
from ..services.file_service import FileService
from ..schemas.file import FileResponse, FileListResponse, FileDownloadResponse
from ..middleware.auth import get_current_user
from ..middleware.quota import check_quota
from ..middleware.rate_limit import limiter
from fastapi import Request

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    description: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a file.
    Supports streaming uploads for large files.
    Automatically enqueues transcoding for video files.
    """
    file_service = FileService(db)
    return await file_service.handle_upload(
        user_id=user["id"], file=file, description=description
    )


@router.get("", response_model=FileListResponse)
async def list_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's files with pagination."""
    file_service = FileService(db)
    return await file_service.list_files(
        user_id=user["id"], page=page, page_size=page_size
    )


@router.get("/{file_id}", response_model=FileResponse)
async def get_file_details(
    file_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get file details by ID."""
    file_service = FileService(db)
    return await file_service.get_file_details(file_id=file_id, user_id=user["id"])


@router.get("/{file_id}/download", response_model=FileDownloadResponse)
async def get_download_url(
    file_id: int,
    expiration: int = Query(3600, ge=60, le=86400),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get presigned download URL for file."""
    file_service = FileService(db)
    return await file_service.get_download_url(
        file_id=file_id, user_id=user["id"], expiration=expiration
    )

