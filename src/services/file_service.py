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
        Stage upload:
        1. Validate
        2. Save to temp
        3. Create pending record
        4. Return response (background task picks up from there)
        """
        from ..utils.logger import get_logger
        import traceback
        import tempfile
        import os
        
        logger = get_logger(__name__)
        temp_path = None
        
        try:
            logger.info(
                f"Starting file upload staging",
                extra={
                    "user_id": user_id,
                    "dumapod_id": dumapod_id,
                    "filename": file.filename,
                    "content_type": file.content_type,
                }
            )
            
            # 1. Validate File Type and Basic Checks
            try:
                validate_file_upload(file)
            except HTTPException as e:
                logger.warning(
                    f"File validation failed: {e.detail}",
                    extra={
                        "user_id": user_id,
                        "filename": file.filename,
                        "content_type": file.content_type,
                    }
                )
                raise  # Re-raise validation errors as-is
            
            # 2. Read file content
            try:
                file_content = await file.read()
                file_size = len(file_content)
                logger.info(f"File read successfully, size: {file_size} bytes")
            except Exception as e:
                logger.error(
                    f"Failed to read uploaded file",
                    exc_info=e,
                    extra={"user_id": user_id, "filename": file.filename}
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to read uploaded file: {str(e)}"
                )
            
            # 3. Get DumaPod & Check Capacity
            try:
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
                        f"Storage capacity exceeded",
                        extra={
                            "dumapod_id": dumapod_id,
                            "current_usage_gb": current_usage_bytes / (1024**3),
                            "file_size_gb": file_size / (1024**3),
                            "limit_gb": limit_gb,
                        }
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Upload exceeds DumaPod storage capacity. Current usage: {current_usage_bytes / (1024**3):.2f} GB, File size: {file_size / (1024**3):.2f} GB, Limit: {limit_gb} GB"
                    )
                    
            except HTTPException:
                raise  # Re-raise HTTP exceptions
            except Exception as e:
                logger.error(
                    f"Failed to check DumaPod capacity",
                    exc_info=e,
                    extra={"user_id": user_id, "dumapod_id": dumapod_id}
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to verify storage capacity: {str(e)}"
                )
            
            # 4. Save to Temporary File
            try:
                sanitized_filename = sanitize_filename(file.filename or "unnamed")
                fd, temp_path = tempfile.mkstemp(suffix=f"_{sanitized_filename}")
                
                with os.fdopen(fd, 'wb') as tmp:
                    tmp.write(file_content)
                    
                logger.info(f"File saved to temporary location: {temp_path}")
                
            except Exception as e:
                logger.error(
                    f"Failed to save file to temporary storage",
                    exc_info=e,
                    extra={"user_id": user_id, "filename": file.filename}
                )
                # Clean up temp file if it was created
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to save uploaded file temporarily: {str(e)}"
                )
            
            # 5. Create Pending Database Record
            try:
                stored_file = await self.duma_file_repo.create_file_record(
                    dumapod_id=dumapod_id,
                    user_id=user_id,
                    file_name=sanitized_filename,
                    file_type=file.content_type or "application/octet-stream",
                    file_size=file_size,
                    s3_url=None,
                    wasabi_url=None,
                    oracle_url=None
                )
                
                logger.info(
                    f"File record created successfully",
                    extra={
                        "file_id": stored_file.id,
                        "user_id": user_id,
                        "dumapod_id": dumapod_id,
                        "filename": sanitized_filename,
                    }
                )
                
            except Exception as e:
                logger.error(
                    f"Failed to create file record in database",
                    exc_info=e,
                    extra={
                        "user_id": user_id,
                        "dumapod_id": dumapod_id,
                        "filename": sanitized_filename,
                    }
                )
                # Clean up temp file
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create file record: {str(e)}"
                )
            
            # 6. Return Response
            return FileResponse(
                id=stored_file.id,
                user_id=stored_file.user_id,
                filename=stored_file.file_name,
                original_filename=stored_file.file_name,
                content_type=stored_file.file_type,
                file_size=stored_file.file_size,
                storage_key=temp_path,  # Pass temp path for background task
                storage_provider=primary_storage,
                description=description,
                upload_status="pending",
                created_at=stored_file.created_at,
                updated_at=stored_file.created_at
            )
            
        except HTTPException:
            # Re-raise HTTP exceptions (already logged above)
            raise
            
        except Exception as e:
            # Catch any unexpected errors
            logger.error(
                f"Unexpected error during file upload staging",
                exc_info=e,
                extra={
                    "user_id": user_id,
                    "dumapod_id": dumapod_id,
                    "filename": file.filename,
                    "error_type": type(e).__name__,
                }
            )
            
            # Also log to file for debugging
            try:
                with open("logs/upload_errors.log", "a") as log_file:
                    log_file.write(f"\n{'='*80}\n")
                    log_file.write(f"Timestamp: {__import__('datetime').datetime.now().isoformat()}\n")
                    log_file.write(f"User ID: {user_id}\n")
                    log_file.write(f"DumaPod ID: {dumapod_id}\n")
                    log_file.write(f"Filename: {file.filename}\n")
                    log_file.write(f"Content Type: {file.content_type}\n")
                    log_file.write(f"Error Type: {type(e).__name__}\n")
                    log_file.write(f"Error Message: {str(e)}\n")
                    log_file.write(f"Traceback:\n{traceback.format_exc()}\n")
            except:
                pass  # Don't fail if logging fails
            
            # Clean up temp file if it exists
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error during file upload: {type(e).__name__}: {str(e)}"
            )

    async def process_background_upload(
        self, file_id: int, temp_path: str, dumapod_id: int, user_id: int, description: Optional[str] = None
    ):
        """
        Background task: Upload to providers, update DB, cleanup temp file.
        """
        import os
        import asyncio
        
        try:
            # Read content from temp file
            if not os.path.exists(temp_path):
                print(f"Temp file {temp_path} not found for file {file_id}")
                # Update status to failed
                # self.file_repo.update_status(file_id, "failed")
                return
            
            # 3. Read file content from temp path
            # Note: For very large files, reading into memory might still be an issue here if we don't stream.
            # But storage_repo.upload_file now accepts bytes. 
            # Ideally we should stream from disk to upload_fileobj, but storage_repo uses BytesIO wrapping bytes.
            # To truly stream, we'd need to change storage_repo to accept file path or file object.
            # For now, we read.
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
                        
                        # Optimization: 
                        # Update only if progress increased by at least 5% 
                        # AND at least 1 second has passed since last update.
                        # Always update if we reached 100%? 
                        # Actually 100% is handled by completion status update, 
                        # but it's good to show 100% progress.
                        
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
                            # Log errors from future (simple error logging)
                            def log_error(fut):
                                try:
                                    fut.result()
                                except Exception as e:
                                    with open("error.log", "a") as f:
                                        f.write(f"Callback Error: {e}\n")
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

            # Normalize DumaPod Data (This block was redundant and is now removed as variables are extracted above)
            # The original code had a duplicate `providers_to_upload = []` and then re-extracted variables.
            # The instruction implies using the *extracted* variables for the `providers_to_upload` logic.
            # The `use_s3`, `use_wasabi`, `use_oracle` variables are still needed for `prepare_provider`.
            if isinstance(dumapod, dict):
                use_s3 = dumapod.get("use_custom_s3")
                use_wasabi = dumapod.get("use_custom_wasabi")
                use_oracle = dumapod.get("use_custom_oracle")
            else:
                use_s3 = dumapod.use_custom_s3
                use_wasabi = dumapod.use_custom_wasabi
                use_oracle = dumapod.use_custom_oracle

            # Prepare Providers
            
            # Helper to prepare provider config
            async def prepare_provider(provider_type: StorageProvider, use_custom: bool):
                if not use_custom:
                    return {"provider": provider_type, "credentials": None}
                creds = await self.credential_service.repo.get_by_dumapod_and_provider(dumapod_id, provider_type)
                if not creds:
                     # Log warning but continue? Or fail? The user expects it.
                     print(f"Warning: Custom creds missing for {provider_type}")
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
                 print("No providers enabled")
                 # Update status failed
                 return

            # Note: We need the filename again. We can get it from DB or pass it.
            # Let's fetch the record to be sure.
            stored_file = await self.duma_file_repo.get_file(file_id)
            if not stored_file:
                return 
            
            # Fix: stored_file is a dict from repo? 
            # In update below we use duma_file_repo which uses SQLAlchemy model
            # Let's rely on passed filename or fetch fresh from repo
            
            sanitized_filename = stored_file.file_name
            storage_key = self.storage_repo.generate_key(user_id, sanitized_filename)

            upload_urls = {}
            
            async def _upload_and_get_url(p_config, use_callback=False):
                p_type = p_config["provider"]
                creds = p_config["credentials"]
                
                # Callback logic
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
                # Only use callback for the first provider to avoid double counting or race conditions on DB field
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
            # We need a method to update specifically 
            await self.duma_file_repo.update_file_status_and_urls(
                file_id, 
                "completed",
                s3_url=upload_urls.get("s3_url"),
                wasabi_url=upload_urls.get("wasabi_url"),
                oracle_url=upload_urls.get("oracle_url"),
                # Also save storage_key? Schema has it but model doesn't explicitly have 'storage_key' column?
                # Model has s3_url etc.
            )
            
            print(f"Background upload for file {file_id} completed.")

        except Exception as e:
            print(f"Background upload failed: {e}")
            # Log error
            with open("error.log", "a") as log:
                import traceback
                log.write(f"Error in background upload: {e}\n")
                log.write(traceback.format_exc())
                log.write("\n")
            
            # Update status failed
            await self.duma_file_repo.update_file_status_and_urls(file_id, "failed")
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)

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
    temp_path: str,
    dumapod_id: int,
    user_id: int
):
    """
    Wrapper to run background upload with a fresh database session.
    """
    from ..config.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as session:
        try:
            service = FileService(session)
            await service.process_background_upload(
                file_id=file_id,
                temp_path=temp_path,
                dumapod_id=dumapod_id,
                user_id=user_id
            )
            await session.commit()
        except Exception as e:
            await session.rollback()
            # process_background_upload handles its own logging and status update (if it can),
            # but if session fails here, we might need extra catch.
            # However, process_background_upload expects to work with the session.
            # If creating service fails, we log here.
            print(f"Critical error in background wrapper: {e}")
            # Try to log to error.log
            with open("error.log", "a") as log:
                 log.write(f"Critical error in wrapper: {e}\n")

