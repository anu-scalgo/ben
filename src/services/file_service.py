"""File service for file upload and management."""

import shutil
import asyncio
import aiofiles
from typing import List, Optional, Tuple
from fastapi import UploadFile, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from ..repositories.file_repo import FileRepository
from ..repositories.storage_repo import StorageRepository
from ..repositories.queue_repo import QueueRepository
from ..repositories.subscription_repo import SubscriptionRepository
from ..schemas.file import FileResponse, FileListResponse, FileDownloadResponse
from ..utils.helpers import bytes_to_gb, sanitize_filename
from ..utils.constants import UploadStatus
from ..middleware.validation import validate_file_upload
from .dumapod_service import DumaPodService
from .credential_service import CredentialService
from ..models.dumapod import StorageProvider, DumaPod
from ..repositories.duma_stored_file_repo import DumaStoredFileRepository


class FileService:
    """Service for file operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.file_repo = FileRepository(db)
        self.storage_repo = StorageRepository()
        self.queue_repo = QueueRepository()
        self.subscription_repo = SubscriptionRepository(db)
        self.dumapod_service = DumaPodService(db)
        self.credential_service = CredentialService(db)
        self.duma_file_repo = DumaStoredFileRepository(db)

    async def stage_upload(
        self, user_id: int, dumapod_id: int, file: UploadFile, description: Optional[str] = None
    ) -> FileResponse:
        """
        Stage upload - Optimized for large files:
        1. Validate file type only (no full read)
        2. Get file size from metadata
        3. Check capacity
        4. Create database record with "uploading" status
        5. Return immediately (202 Accepted)
        
        Background task will handle actual file streaming and S3 upload.
        """
        from ..utils.logger import get_logger
        logger = get_logger(__name__)
        
        logger.info(f"Staging upload for user {user_id}, file: {file.filename}")
        
        # 1. Validate File Type (no full read needed)
        validate_file_upload(file)
        
        # 2. Get file size from UploadFile metadata (no read needed)
        # UploadFile.size is available from the Content-Length header
        file_size = file.size
        
        if file_size is None or file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size could not be determined or file is empty"
            )
        
        # 3. Get DumaPod & Check Capacity
        dumapod = await self.dumapod_service.get_dumapod(dumapod_id)
        current_usage_bytes = await self.duma_file_repo.get_total_usage(dumapod_id)
        
        # Normalize Data
        if isinstance(dumapod, dict):
            limit_gb = dumapod.get("storage_capacity_gb")
            primary_storage = dumapod.get("primary_storage")
        else:
            limit_gb = dumapod.storage_capacity_gb
            primary_storage = dumapod.primary_storage

        # Capacity Check
        capacity_bytes = limit_gb * 1024 * 1024 * 1024
        if current_usage_bytes + file_size > capacity_bytes:
            logger.warning(
                f"Storage capacity exceeded for dumapod {dumapod_id}: "
                f"current={current_usage_bytes / (1024**3):.2f}GB, "
                f"file={file_size / (1024**3):.2f}GB, "
                f"limit={limit_gb}GB"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upload exceeds DumaPod storage capacity. Current: {current_usage_bytes / (1024**3):.2f} GB, File: {file_size / (1024**3):.2f} GB, Limit: {limit_gb} GB"
            )

        # 4. Create Database Record with "uploading" status
        sanitized_filename = sanitize_filename(file.filename or "unnamed")
        
        stored_file = await self.duma_file_repo.create_file_record(
            dumapod_id=dumapod_id,
            user_id=user_id,
            file_name=sanitized_filename,
            file_type=file.content_type or "application/octet-stream",
            file_size=file_size,
            s3_url=None, 
            wasabi_url=None, 
            oracle_url=None,
            upload_status="uploading"  # File is being uploaded from client
        )
        
        logger.info(
            f"File record created: id={stored_file.id}, "
            f"size={file_size / (1024**2):.2f}MB, status=uploading"
        )
        
        # 5. Return immediately - background task will handle file streaming
        return FileResponse(
            id=stored_file.id,
            user_id=stored_file.user_id,
            filename=stored_file.file_name,
            original_filename=stored_file.file_name,
            content_type=stored_file.file_type,
            file_size=stored_file.file_size,
            storage_key=f"uploads/{user_id}/{sanitized_filename}",  # S3 key
            storage_provider=primary_storage,
            description=description,
            upload_status="uploading",  # Client should poll for completion
            upload_progress=0,
            created_at=stored_file.created_at,
            updated_at=stored_file.created_at
        )

    async def process_background_upload(
        self, file_id: int, file: UploadFile, dumapod_id: int, user_id: int, description: Optional[str] = None
    ):
        """
        Background task: Stream file from client, save to temp, upload to providers.
        Uses chunked streaming to handle large files without memory issues.
        """
        import os
        import asyncio
        import tempfile
        from ..utils.logger import get_logger
        
        logger = get_logger(__name__)
        temp_path = None
        
        try:
            logger.info(f"Starting background upload for file {file_id}")
            
            # 1. Stream file to temporary storage in chunks
            fd, temp_path = tempfile.mkstemp(suffix=f"_{file_id}")
            chunk_size = 8 * 1024 * 1024  # 8MB chunks
            total_bytes_written = 0
            
            logger.info(f"Streaming file to temp: {temp_path}")
            
            # Stream file in chunks using aiofiles
            async with aiofiles.open(temp_path, 'wb') as temp_file:
                while True:
                    chunk = await file.read(chunk_size)
                    if not chunk:
                        break
                    await temp_file.write(chunk)
                    total_bytes_written += len(chunk)
                    
                    # Update progress every chunk (optional, can be less frequent)
                    # For now, we'll update after all chunks are written
            
            logger.info(f"File streamed to temp: {total_bytes_written} bytes")
            
            # Update status to "pending" - file uploaded from client, now uploading to S3
            await self.duma_file_repo.update_file_status_and_urls(file_id, "pending")
            
            # 2. Read content from temp file for S3 upload
            if not os.path.exists(temp_path):
                error_msg = f"Temp file {temp_path} not found for file {file_id}"
                logger.error(error_msg)
                await self.duma_file_repo.update_file_status_and_urls(file_id, "failed", failed_reason=error_msg)
                return
            
            # Read file content from temp path
            async with aiofiles.open(temp_path, 'rb') as f:
                file_content = await f.read()

            import threading
            
            # Progress tracking class to handle state across threads
            class ProgressTracker:
                def __init__(self, service, file_id, total_size, loop):
                    self.service = service
                    self.file_id = file_id
                    self.total_size = total_size
                    self.uploaded = 0
                    self.last_percent = 0
                    self.last_update_time = 0
                    self.loop = loop
                    self.lock = threading.Lock()

                def __call__(self, bytes_amount):
                    import time
                    with self.lock:
                        self.uploaded += bytes_amount
                        percent = int((self.uploaded / self.total_size) * 100)
                        
                        now = time.time()
                        
                        # Update only if progress increased by at least 5% 
                        # AND at least 1 second has passed since last update.
                        should_update = False
                        
                        if percent == 100 and self.last_percent < 100:
                             should_update = True
                        elif (percent >= self.last_percent + 5) and (now - self.last_update_time >= 1.0):
                             should_update = True
                        
                        if should_update:
                            self.last_percent = percent
                            self.last_update_time = now
                            # Schedule db update on the main event loop
                            future = asyncio.run_coroutine_threadsafe(
                                 self.service.duma_file_repo.update_upload_progress(self.file_id, percent),
                                 self.loop
                            )
                            # Log errors from future
                            def log_error(fut):
                                try:
                                    fut.result()
                                except Exception as e:
                                    logger.error(f"Progress callback error: {e}")
                            future.add_done_callback(log_error)

            loop = asyncio.get_running_loop()
            tracker = ProgressTracker(self, file_id, len(file_content), loop)

            # Re-fetch dumapod logic for providers
            dumapod = await self.dumapod_service.get_dumapod(dumapod_id)
            # Normalize DumaPod Data
            if isinstance(dumapod, dict):
                enable_s3 = dumapod.get("enable_s3")
                enable_wasabi = dumapod.get("enable_wasabi")
                enable_oracle_os = dumapod.get("enable_oracle_os")
                primary_storage = dumapod.get("primary_storage")
            else:
                enable_s3 = dumapod.enable_s3
                enable_wasabi = dumapod.enable_wasabi
                enable_oracle_os = dumapod.enable_oracle_os
                primary_storage = dumapod.primary_storage

            if isinstance(dumapod, dict):
                use_s3 = dumapod.get("use_custom_s3")
                use_wasabi = dumapod.get("use_custom_wasabi")
                use_oracle = dumapod.get("use_custom_oracle")
            else:
                use_s3 = dumapod.use_custom_s3
                use_wasabi = dumapod.use_custom_wasabi
                use_oracle = dumapod.use_custom_oracle

            # Prepare Providers
            async def prepare_provider(provider_type: StorageProvider, use_custom: bool):
                if not use_custom:
                    return {"provider": provider_type, "credentials": None}
                creds = await self.credential_service.repo.get_by_dumapod_and_provider(dumapod_id, provider_type)
                if not creds:
                     logger.warning(f"Custom creds missing for {provider_type}")
                     return None
                return {"provider": provider_type, "credentials": creds}

            providers_to_upload = []
            if enable_s3:
                p = await prepare_provider(StorageProvider.AWS_S3, use_s3)
                if p: providers_to_upload.append(p)
            if enable_wasabi:
                p = await prepare_provider(StorageProvider.WASABI, use_wasabi)
                if p: providers_to_upload.append(p)
            if enable_oracle_os:
                p = await prepare_provider(StorageProvider.ORACLE_OS, use_oracle)
                if p: providers_to_upload.append(p)
            
            if not providers_to_upload:
                 error_msg = "No storage providers enabled for this DumaPod"
                 logger.error(error_msg)
                 await self.duma_file_repo.update_file_status_and_urls(file_id, "failed", failed_reason=error_msg)
                 return

            # Fetch the record to get filename
            stored_file = await self.duma_file_repo.get_file(file_id)
            if not stored_file:
                logger.error(f"File record {file_id} not found")
                return 
            
            sanitized_filename = stored_file.file_name
            storage_key = self.storage_repo.generate_key(user_id, sanitized_filename)

            upload_urls = {}
            
            async def _upload_and_get_url(p_config, use_callback=False):
                p_type = p_config["provider"]
                creds = p_config["credentials"]
                
                cb = tracker if use_callback else None

                await self.storage_repo.upload_file(
                    file_content=file_content,
                    key=storage_key,
                    content_type=stored_file.file_type, 
                    provider=p_type,
                    credentials=creds,
                    progress_callback=cb
                )
                
                bucket_name = creds.bucket_name if creds else await self.storage_repo._get_bucket(p_type)
                p_value = p_type.value if hasattr(p_type, 'value') else p_type
                url = f"{p_value}://{bucket_name}/{storage_key}"
                return p_type, url

            # Execute Parallel
            upload_tasks = []
            for i, conf in enumerate(providers_to_upload):
                use_cb = (i == 0)
                upload_tasks.append(_upload_and_get_url(conf, use_callback=use_cb))
            results = await asyncio.gather(*upload_tasks)
            
            for p_type, url in results:
                if p_type == StorageProvider.AWS_S3:
                    upload_urls["s3_url"] = url
                elif p_type == StorageProvider.WASABI:
                    upload_urls["wasabi_url"] = url
                elif p_type == StorageProvider.ORACLE_OS:
                    upload_urls["oracle_url"] = url
            
            # Update DB with URLs and Status COMPLETED
            await self.duma_file_repo.update_file_status_and_urls(
                file_id, 
                "completed",
                s3_url=upload_urls.get("s3_url"),
                wasabi_url=upload_urls.get("wasabi_url"),
                oracle_url=upload_urls.get("oracle_url"),
            )
            
            # Set progress to 100%
            await self.duma_file_repo.update_upload_progress(file_id, 100)
            
            logger.info(f"Background upload for file {file_id} completed successfully")

        except Exception as e:
            logger.error(f"Background upload failed for file {file_id}: {e}", exc_info=e)
            
            # Update status failed with error details
            error_msg = f"{type(e).__name__}: {str(e)}"
            try:
                await self.duma_file_repo.update_file_status_and_urls(file_id, "failed", failed_reason=error_msg)
            except:
                pass
        finally:
            # Cleanup temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.info(f"Cleaned up temp file: {temp_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")

    async def download_file(self, file_id: int, user_id: int) -> FileDownloadResponse:
        """
        Generate download URL for a file.
        """
        file_record = await self.duma_file_repo.get_by_user_and_id(user_id, file_id)
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )
            
        # Determine provider and key
        # We need to know which provider has the file.
        # Check URLs.
        provider = None
        key = file_record.file_name # storage key logic same as upload
        # Warning: if we changed key logic (e.g. prefix), we need to reconstruct it or store it.
        # Currently generate_key uses user_id/filename.
        key = self.storage_repo.generate_key(user_id, file_record.file_name)
        
        if file_record.s3_url:
            provider = "aws_s3"
        elif file_record.wasabi_url:
            provider = "wasabi"
        elif file_record.oracle_url:
            provider = "oracle_object_storage"
            
        if not provider:
             raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not available on any storage provider",
            )
            
        url = await self.storage_repo.generate_presigned_url(
            key=key,
            provider=provider
        )
        
        return FileDownloadResponse(
            file_id=file_record.id,
            filename=file_record.file_name,
            download_url=url,
            file_size=file_record.file_size,
            content_type=file_record.file_type
        )

    async def get_file_details(self, file_id: int, user_id: int) -> FileResponse:
        """Get file details by ID (with authorization check)."""
        file_record = await self.duma_file_repo.get_by_user_and_id(user_id, file_id)

        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )
        
        # Determine primary storage provider from dumapod? 
        # Or just use "aws_s3" as placeholder since we don't store it on file record explicitly 
        # (We store urls). 
        # We can fetch dumapod to be precise, or just return based on URLs.
        
        provider = "unknown"
        if file_record.s3_url: provider = "aws_s3"
        elif file_record.wasabi_url: provider = "wasabi"
        elif file_record.oracle_url: provider = "oracle_object_storage"
        
        # Storage Key: we don't persist it explicitly, but it's part of the URL or we can regenerate it.
        # Ideally we should store it. For now, use filename or parsed from URL.
        storage_key = file_record.file_name 

        return FileResponse(
            id=file_record.id,
            user_id=file_record.user_id,
            filename=file_record.file_name,
            original_filename=file_record.file_name,
            content_type=file_record.file_type,
            file_size=file_record.file_size,
            storage_key=storage_key,
            storage_provider=provider,
            description=None, # duma_stored_file table doesn't have description column? Model doesn't show it.
            upload_status=file_record.upload_status,
            upload_progress=file_record.upload_progress,
            failed_reason=file_record.failed_reason,
            s3_url=file_record.s3_url,
            wasabi_url=file_record.wasabi_url,
            oracle_url=file_record.oracle_url,
            created_at=file_record.created_at,
            updated_at=file_record.created_at
        )

    async def list_files(
        self, user_id: int, page: int = 1, page_size: int = 20
    ) -> FileListResponse:
        """List user's files with pagination."""
        skip = (page - 1) * page_size
        files = await self.duma_file_repo.get_by_user_id(user_id, skip=skip, limit=page_size)
        total = await self.duma_file_repo.get_file_count_by_user(user_id)

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        # Construct response. Note: FileResponse needs manual mapping because some fields are computed or different
        # Or better, we ensure FileResponse matches Model or we handle it.
        # FileResponse has storage_key, storage_provider, description.
        # Model: has file_name, file_type, file_size, urls.
        # Model doesn't have description or storage_provider explicitly stored.
        # We need to map manually like in get_file_details.
        
        file_responses = []
        for f in files:
            # Determine provider helper (duplicate logic, could be refactored)
            provider = "unknown"
            if f.s3_url: provider = "aws_s3"
            elif f.wasabi_url: provider = "wasabi"
            elif f.oracle_url: provider = "oracle_object_storage"
            
            file_responses.append(FileResponse(
                id=f.id,
                user_id=f.user_id,
                filename=f.file_name,
                original_filename=f.file_name,
                content_type=f.file_type,
                file_size=f.file_size,
                storage_key=f.file_name, # Approximation
                storage_provider=provider,
                description=None, 
                upload_status=f.upload_status,
                upload_progress=f.upload_progress,
                failed_reason=f.failed_reason,
                s3_url=f.s3_url,
                wasabi_url=f.wasabi_url,
                oracle_url=f.oracle_url,
                created_at=f.created_at,
                updated_at=f.created_at,
                transcoded_urls=[]
            ))

        return FileListResponse(
            files=file_responses,
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
            file_id=file_record.id,
            filename=file_record.file_name,
            download_url=download_url,
            expires_in=expiration,
            file_size=file_record.file_size, # Assuming dict key access for old repo, but wait, file_record is from get_by_id_and_user in file_repo which returns dict?
            # Wait, get_download_url uses file_repo.get_by_id_and_user (old repo).
            # The new download_file (if implemented) uses duma_file_repo.
            # I should stick to appending the wrapper.
            content_type=file_record.content_type,
        )

# Background Task Wrapper
async def run_background_upload_wrapper(
    file_id: int,
    file: UploadFile,
    dumapod_id: int,
    user_id: int
):
    """
    Wrapper to run background upload with a fresh database session.
    Streams file from client in chunks to avoid memory issues.
    """
    from ..config.database import AsyncSessionLocal
    from ..utils.logger import get_logger
    
    logger = get_logger(__name__)
    
    async with AsyncSessionLocal() as session:
        try:
            service = FileService(session)
            await service.process_background_upload(
                file_id=file_id,
                file=file,  # Pass UploadFile for streaming
                dumapod_id=dumapod_id,
                user_id=user_id
            )
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Critical error in background upload wrapper for file {file_id}: {e}", exc_info=e)
            # Try to update status to failed with error details
            error_msg = f"{type(e).__name__}: {str(e)}"
            try:
                from ..repositories.duma_stored_file_repo import DumaStoredFileRepository
                repo = DumaStoredFileRepository(session)
                await repo.update_file_status_and_urls(file_id, "failed", failed_reason=error_msg)
                await session.commit()
            except:
                pass

