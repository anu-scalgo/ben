"""File upload and management routes."""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from ..config.database import get_db
from ..services.file_service import FileService
from ..schemas.file import FileResponse, FileListResponse, FileDownloadResponse
from ..middleware.auth import get_current_user
from ..models.user import User
from ..middleware.quota import check_quota
from ..middleware.rate_limit import limiter
from fastapi import Request

from fastapi import BackgroundTasks

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FileResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("20/minute")
async def upload_file(
    request: Request,
    background_tasks: BackgroundTasks,
    dumapod_id: int = Form(...),
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a file to a specific DumaPod.
    Supports streaming uploads for large files.
    Automatically enqueues transcoding for video files.
    """
    file_service = FileService(db)
    response = await file_service.stage_upload(
        user_id=user.id, dumapod_id=dumapod_id, file=file, description=description
    )
    
    from ..services.file_service import run_background_upload_wrapper
    
    background_tasks.add_task(
        run_background_upload_wrapper,
        file_id=response.id,
        temp_path=response.storage_key,
        dumapod_id=dumapod_id,
        user_id=user.id
    )
    
    return response


@router.get("", response_model=FileListResponse)
async def list_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's files with pagination."""
    file_service = FileService(db)
    return await file_service.list_files(
        user_id=user.id, page=page, page_size=page_size
    )


@router.get("/{file_id}", response_model=FileResponse)
async def get_file_details(
    file_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get file details by ID."""
    file_service = FileService(db)
    return await file_service.get_file_details(file_id=file_id, user_id=user.id)


@router.get("/{file_id}/download", response_model=FileDownloadResponse)
async def get_download_url(
    file_id: int,
    expiration: int = Query(3600, ge=60, le=86400),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get presigned download URL for file."""
    file_service = FileService(db)
    return await file_service.get_download_url(
        file_id=file_id, user_id=user.id, expiration=expiration
    )

