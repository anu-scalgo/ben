

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
