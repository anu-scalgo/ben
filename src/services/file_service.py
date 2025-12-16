"""File service for file upload and management."""

from typing import List, Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..repositories.file_repo import FileRepository
from ..repositories.storage_repo import StorageRepository
from ..repositories.queue_repo import QueueRepository
from ..repositories.subscription_repo import SubscriptionRepository
from ..schemas.file import FileResponse, FileListResponse, FileDownloadResponse
from ..utils.helpers import bytes_to_gb, sanitize_filename
from ..utils.constants import UploadStatus
from ..middleware.validation import validate_file_upload


class FileService:
    """Service for file operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.file_repo = FileRepository(db)
        self.storage_repo = StorageRepository()
        self.queue_repo = QueueRepository()
        self.subscription_repo = SubscriptionRepository(db)

    async def handle_upload(
        self, user_id: int, file: UploadFile, description: Optional[str] = None
    ) -> FileResponse:
        """
        Handle file upload: validate, upload to storage, create metadata, enqueue transcoding.
        """
        # Validate file
        validate_file_upload(file)

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Check quota
        subscription = await self.subscription_repo.get_by_user_id(user_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No active subscription found",
            )

        storage_gb = bytes_to_gb(file_size)
        if subscription["used_storage_gb"] + storage_gb > subscription["storage_limit_gb"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Storage quota exceeded",
            )

        # Generate storage key
        sanitized_filename = sanitize_filename(file.filename or "unnamed")
        storage_key = self.storage_repo.generate_key(user_id, sanitized_filename)

        # Upload to storage
        await self.storage_repo.upload_file(
            file_content=file_content,
            key=storage_key,
            content_type=file.content_type or "application/octet-stream",
        )

        # Create file metadata
        file_record = await self.file_repo.create_file(
            user_id=user_id,
            filename=storage_key.split("/")[-1],
            original_filename=file.filename or "unnamed",
            content_type=file.content_type or "application/octet-stream",
            file_size=file_size,
            storage_key=storage_key,
            storage_provider="s3",  # Would get from config
            description=description,
        )

        # Update quota
        await self.subscription_repo.update_quota(
            subscription["id"], storage_gb=storage_gb, file_count=1
        )

        # Enqueue transcoding if video file
        if file.content_type and file.content_type.startswith("video/"):
            await self.file_repo.update_upload_status(
                file_record["id"], UploadStatus.PROCESSING.value
            )
            self.queue_repo.enqueue_transcode(
                file_id=file_record["id"],
                storage_key=storage_key,
                storage_provider="s3",
                output_formats=["mp4", "webm"],
            )

        return FileResponse(
            id=file_record["id"],
            user_id=file_record["user_id"],
            filename=file_record["filename"],
            original_filename=file_record["original_filename"],
            content_type=file_record["content_type"],
            file_size=file_record["file_size"],
            storage_key=file_record["storage_key"],
            storage_provider=file_record["storage_provider"],
            description=file_record.get("description"),
            transcoded_urls=file_record.get("transcoded_urls", []),
            upload_status=file_record["upload_status"],
            created_at=file_record.get("created_at", ""),
            updated_at=file_record.get("updated_at", ""),
        )

    async def get_file_details(self, file_id: int, user_id: int) -> FileResponse:
        """Get file details by ID (with authorization check)."""
        file_record = await self.file_repo.get_by_id_and_user(file_id, user_id)

        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )

        return FileResponse(**file_record)

    async def list_files(
        self, user_id: int, page: int = 1, page_size: int = 20
    ) -> FileListResponse:
        """List user's files with pagination."""
        skip = (page - 1) * page_size
        files = await self.file_repo.get_by_user_id(user_id, skip=skip, limit=page_size)
        total = await self.file_repo.get_file_count_by_user(user_id)

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return FileListResponse(
            files=[FileResponse(**f) for f in files],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_download_url(
        self, file_id: int, user_id: int, expiration: int = 3600
    ) -> FileDownloadResponse:
        """Generate presigned download URL for file."""
        file_record = await self.file_repo.get_by_id_and_user(file_id, user_id)

        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )

        download_url = await self.storage_repo.generate_presigned_url(
            file_record["storage_key"], expiration=expiration
        )

        return FileDownloadResponse(
            file_id=file_record["id"],
            filename=file_record["original_filename"],
            download_url=download_url,
            expires_in=expiration,
            file_size=file_record["file_size"],
            content_type=file_record["content_type"],
        )

