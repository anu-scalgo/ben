"""File upload and management routes."""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from ..config.database import get_db
from ..services.file_service import FileService
from ..schemas.file import (
    FileResponse,
    FileListResponse,
    FileDownloadResponse,
    InitiateUploadRequest,
    PresignedUploadResponse,
    InitiateMultipartUploadRequest,
    InitiateMultipartUploadResponse,
    CompleteMultipartUploadRequest,
    AbortMultipartUploadRequest,
)
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
    Returns immediately (202 Accepted) - file streams in background.
    Poll the file status endpoint to check upload progress.
    """
    file_service = FileService(db)
    response = await file_service.stage_upload(
        user_id=user.id, dumapod_id=dumapod_id, file=file, description=description
    )
    
    from ..services.file_service import run_background_upload_wrapper
    
    # Pass file object to background task for streaming
    background_tasks.add_task(
        run_background_upload_wrapper,
        file_id=response.id,
        file=file,  # Pass UploadFile for streaming
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


@router.post("/initiate-upload", response_model=PresignedUploadResponse, status_code=status.HTTP_200_OK)
@limiter.limit("20/minute")
async def initiate_direct_upload(
    request: Request,
    upload_request: InitiateUploadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate direct upload to S3 - Step 1 of 2.
    
    Returns a presigned URL that the client can use to upload the file directly to S3/Wasabi/Oracle.
    This bypasses the server for file data transfer, improving upload speed and reducing server load.
    
    **Flow**:
    1. Client calls this endpoint with file metadata
    2. Server validates and returns presigned URL
    3. Client uploads file directly to S3 using the presigned URL
    4. Client calls /confirm-upload/{file_id} to finalize
    """
    file_service = FileService(db)
    return await file_service.initiate_direct_upload(
        user_id=user.id,
        dumapod_id=upload_request.dumapod_id,
        filename=upload_request.filename,
        content_type=upload_request.content_type,
        file_size=upload_request.file_size,
        description=upload_request.description
    )


@router.post("/confirm-upload/{file_id}", response_model=FileResponse, status_code=status.HTTP_200_OK)
async def confirm_direct_upload(
    file_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm upload completion - Step 2 of 2.
    
    Call this endpoint after successfully uploading the file to S3 using the presigned URL.
    The server will verify the file exists in storage and update the database.
    
    **Flow**:
    1. Client uploads file to S3 using presigned URL from /initiate-upload
    2. Client calls this endpoint to confirm upload
    3. Server verifies file exists in S3
    4. Server updates database status to 'completed'
    5. Returns complete file details
    """
    file_service = FileService(db)
    return await file_service.confirm_upload(file_id=file_id, user_id=user.id)


@router.post("/initiate-multipart-upload", response_model=InitiateMultipartUploadResponse)
async def initiate_multipart_upload(
    request: InitiateMultipartUploadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate multipart upload for large files (>100MB recommended).
    
    Returns presigned URLs for each part that the client uploads directly to S3.
    """
    file_service = FileService(db)
    return await file_service.initiate_multipart_upload(
        user_id=user.id,
        dumapod_id=request.dumapod_id,
        filename=request.filename,
        content_type=request.content_type,
        file_size=request.file_size,
        part_size=request.part_size,
        description=request.description
    )


@router.post("/complete-multipart-upload/{file_id}", response_model=FileResponse)
async def complete_multipart_upload(
    file_id: int,
    request: CompleteMultipartUploadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Complete multipart upload after all parts have been uploaded to S3.
    
    Provide the upload_id and list of parts with their ETags.
    """
    file_service = FileService(db)
    return await file_service.complete_multipart_upload(
        file_id=file_id,
        user_id=user.id,
        upload_id=request.upload_id,
        parts=[{"part_number": p.part_number, "etag": p.etag} for p in request.parts]
    )


@router.post("/abort-multipart-upload/{file_id}")
async def abort_multipart_upload(
    file_id: int,
    request: AbortMultipartUploadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Abort multipart upload and clean up uploaded parts.
    
    Use this if the upload fails or is cancelled.
    """
    file_service = FileService(db)
    return await file_service.abort_multipart_upload(
        file_id=file_id,
        user_id=user.id,
        upload_id=request.upload_id
    )
