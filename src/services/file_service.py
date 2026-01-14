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

    async def handle_upload(
        self, user_id: int, dumapod_id: int, file: UploadFile, description: Optional[str] = None
    ) -> FileResponse:
        """
        Handle file upload: validate, capacity check, upload to multiple providers, create metadata.
        """
        # Validate file
        validate_file_upload(file)

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # 1. Get DumaPod & Check Capacity
        dumapod = await self.dumapod_service.get_dumapod(dumapod_id)
        current_usage_bytes = await self.duma_file_repo.get_total_usage(dumapod_id)
        
        # Normalize DumaPod Data
        if isinstance(dumapod, dict):
            limit_gb = dumapod.get("storage_capacity_gb")
            
            enable_s3 = dumapod.get("enable_s3")
            enable_wasabi = dumapod.get("enable_wasabi")
            enable_oracle = dumapod.get("enable_oracle_os")
            
            use_s3 = dumapod.get("use_custom_s3")
            use_wasabi = dumapod.get("use_custom_wasabi")
            use_oracle = dumapod.get("use_custom_oracle")
            
            primary_storage = dumapod.get("primary_storage")
        else:
            limit_gb = dumapod.storage_capacity_gb
            
            enable_s3 = dumapod.enable_s3
            enable_wasabi = dumapod.enable_wasabi
            enable_oracle = dumapod.enable_oracle_os
            
            use_s3 = dumapod.use_custom_s3
            use_wasabi = dumapod.use_custom_wasabi
            use_oracle = dumapod.use_custom_oracle
            
            primary_storage = dumapod.primary_storage

        # Convert capacity to bytes (GB -> Bytes)
        capacity_bytes = limit_gb * 1024 * 1024 * 1024
        
        if current_usage_bytes + file_size > capacity_bytes:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upload exceeds DumaPod storage capacity. Limit: {limit_gb} GB."
            )

        # 2. Determine Enabled Providers and Credentials
        providers_to_upload = []
        
        # Helper to prepare provider config
        async def prepare_provider(provider_type: StorageProvider, use_custom: bool):
            if not use_custom:
                # Use default credentials
                return {"provider": provider_type, "credentials": None}
            
            # Fetch custom credentials
            creds = await self.credential_service.repo.get_by_dumapod_and_provider(dumapod_id, provider_type)
            if not creds:
                 raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Custom credentials for {provider_type} enabled but not found."
                )
            return {"provider": provider_type, "credentials": creds}

        # Check Providers
        if enable_s3:
            providers_to_upload.append(await prepare_provider(StorageProvider.AWS_S3, use_s3))
        if enable_wasabi:
             providers_to_upload.append(await prepare_provider(StorageProvider.WASABI, use_wasabi))
        if enable_oracle:
             providers_to_upload.append(await prepare_provider(StorageProvider.ORACLE_OS, use_oracle))
             
        if not providers_to_upload:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No storage providers enabled for this DumaPod."
            )

        # 3. Upload to All Enabled Providers
        sanitized_filename = sanitize_filename(file.filename or "unnamed")
        storage_key = self.storage_repo.generate_key(user_id, sanitized_filename)
        
        upload_urls = {}
        
        for p_config in providers_to_upload:
            p_type = p_config["provider"]
            creds = p_config["credentials"]
            
            # Upload
            await self.storage_repo.upload_file(
                file_content=file_content,
                key=storage_key,
                content_type=file.content_type or "application/octet-stream",
                provider=p_type,
                credentials=creds
            )
            
            # Generate URL (Presigned for download, or just key/location reference?)
            # Requirement says "save that return file links". 
            # Ideally we save the Key, but if we need a link, maybe a permanent public link or just the key?
            # "file link from that services will saved" -> implies URL.
            # But S3 private buckets have expiring URLs. 
            # For now, let's store the Key or try to generate a long-lived URL if possible, 
            # OR simply store the Storage Key and generate URLs on read.
            # However, logic explicitly asks to SAVE file links. 
            # I will generate specific URLs for now, possibly presigned with long duration or public URL structure.
            # Given typical restrictions, storing the KEY + Provider is best practice, but adhering to prompt:
            # "receive the response of the storage services and the file link from that services will saved"
            # I'll store the object URL (e.g. s3://bucket/key or https://bucket.s3.region.amazonaws.com/key).
            
            # Let's construct a standard HTTP URL for reference if possible, or just the S3 URI.
            bucket_name = creds.bucket_name if creds else await self.storage_repo._get_bucket(p_type)
            # Simple construction for now, ideally repo has a method `get_object_url`.
            # I'll rely on a new helper or simple string formatting.
            
            p_value = p_type.value if hasattr(p_type, 'value') else p_type
            url = f"{p_value}://{bucket_name}/{storage_key}" # Placeholder URI format
            if p_type == StorageProvider.AWS_S3:
                upload_urls["s3_url"] = url
            elif p_type == StorageProvider.WASABI:
                upload_urls["wasabi_url"] = url
            elif p_type == StorageProvider.ORACLE_OS:
                upload_urls["oracle_url"] = url

        # 4. Save Metadata
        stored_file = await self.duma_file_repo.create_file_record(
            dumapod_id=dumapod_id,
            user_id=user_id,
            file_name=sanitized_filename,
            file_type=file.content_type or "application/octet-stream",
            file_size=file_size,
            s3_url=upload_urls.get("s3_url"),
            wasabi_url=upload_urls.get("wasabi_url"),
            oracle_url=upload_urls.get("oracle_url")
        )

        return FileResponse(
            id=stored_file.id,
            user_id=stored_file.user_id,
            filename=stored_file.file_name,
            original_filename=stored_file.file_name,
            content_type=stored_file.file_type,
            file_size=stored_file.file_size,
            storage_key=storage_key, # Keeping compatibility with response schema
            storage_provider=primary_storage, # Primary as reference
            description=description,
            upload_status="completed",
            
            s3_url=stored_file.s3_url,
            wasabi_url=stored_file.wasabi_url,
            oracle_url=stored_file.oracle_url,
            
            created_at=stored_file.created_at,
            updated_at=stored_file.created_at # Using created_at for updated_at placeholder
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

