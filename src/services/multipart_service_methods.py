    async def initiate_multipart_upload(
        self,
        user_id: int,
        dumapod_id: int,
        filename: str,
        content_type: str,
        file_size: int,
        part_size: Optional[int] = None,
        description: Optional[str] = None
    ):
        """Initiate multipart upload for large files."""
        from ..schemas.file import InitiateMultipartUploadResponse, MultipartPartInfo
        from ..utils.helpers import sanitize_filename
        
        # 1. Validate file size
        from ..config import settings
        # Skip file size check if MAX_FILE_SIZE_MB is set to 0 (unlimited)
        if settings.max_file_size_mb > 0 and file_size > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum allowed size of {settings.max_file_size_mb}MB"
            )
        
        # 2. Check capacity
        current_usage_bytes = await self.duma_file_repo.get_total_usage(dumapod_id)
        dumapod = await self.dumapod_service.get_dumapod(dumapod_id)
        
        if isinstance(dumapod, dict):
            limit_gb = dumapod.get("storage_capacity_gb")
            primary_storage = dumapod.get("primary_storage")
        else:
            limit_gb = dumapod.storage_capacity_gb
            primary_storage = dumapod.primary_storage
        
        limit_bytes = limit_gb * (1024 ** 3)
        if current_usage_bytes + file_size > limit_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upload exceeds DumaPod storage capacity"
            )
        
        # 3. Calculate part size if not provided
        if part_size is None:
            part_size, total_parts = self.storage_repo.calculate_part_size(file_size)
        else:
            import math
            total_parts = math.ceil(file_size / part_size)
        
        # 4. Create database record
        sanitized_filename = sanitize_filename(filename)
        storage_key = self.storage_repo.generate_key(user_id, sanitized_filename)
        
        stored_file = await self.duma_file_repo.create_file_record(
            dumapod_id=dumapod_id,
            user_id=user_id,
            file_name=sanitized_filename,
            file_type=content_type,
            file_size=file_size,
            storage_key=storage_key,
            upload_status="pending_multipart"
        )
        
        # 5. Initiate multipart upload in S3
        try:
            provider_value = primary_storage.value if hasattr(primary_storage, 'value') else primary_storage
            
            upload_id = await self.storage_repo.initiate_multipart_upload(
                key=storage_key,
                content_type=content_type,
                provider=provider_value
            )
            
            # 6. Generate presigned URLs for all parts
            parts_data = await self.storage_repo.generate_multipart_presigned_urls(
                key=storage_key,
                upload_id=upload_id,
                total_parts=total_parts,
                provider=provider_value
            )
            
            # 7. Update database with multipart info
            from sqlalchemy import text
            stmt = text(
                "UPDATE duma_stored_files SET multipart_upload_id = :upload_id, "
                "total_parts = :total_parts WHERE id = :id"
            )
            await self.duma_file_repo.session.execute(
                stmt.bindparams(upload_id=upload_id, total_parts=total_parts, id=stored_file.id)
            )
            await self.duma_file_repo.session.commit()
            
            # 8. Format response
            parts = [
                MultipartPartInfo(
                    part_number=p['part_number'],
                    upload_url=p['upload_url'],
                    size=part_size if p['part_number'] < total_parts else (file_size % part_size or part_size)
                )
                for p in parts_data
            ]
            
            return InitiateMultipartUploadResponse(
                file_id=stored_file.id,
                upload_id=upload_id,
                storage_key=storage_key,
                parts=parts,
                total_parts=total_parts,
                part_size=part_size,
                expires_in=3600,
                storage_provider=provider_value
            )
            
        except Exception as e:
            logger.error(f"Failed to initiate multipart upload: {e}")
            await self.duma_file_repo.update_file_status_and_urls(
                stored_file.id, "failed", failed_reason=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initiate multipart upload: {str(e)}"
            )

    async def complete_multipart_upload(
        self,
        file_id: int,
        user_id: int,
        upload_id: str,
        parts: list
    ):
        """Complete multipart upload."""
        from ..schemas.file import FileResponse
        
        # 1. Get file record
        file_record = await self.duma_file_repo.get_by_user_and_id(user_id, file_id)
        
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        if file_record.upload_status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File upload already completed"
            )
        
        if file_record.multipart_upload_id != upload_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid upload ID"
            )
        
        # 2. Get DumaPod info
        dumapod = await self.dumapod_service.get_dumapod(file_record.dumapod_id)
        if isinstance(dumapod, dict):
            primary_storage = dumapod.get("primary_storage")
        else:
            primary_storage = dumapod.primary_storage
        
        # 3. Complete multipart upload in S3
        try:
            provider_value = primary_storage.value if hasattr(primary_storage, 'value') else primary_storage
            
            await self.storage_repo.complete_multipart_upload(
                key=file_record.storage_key,
                upload_id=upload_id,
                parts=parts,
                provider=provider_value
            )
            
            # 4. Generate storage URLs
            s3_url = f"{provider_value}://{await self.storage_repo._get_bucket(provider_value)}/{file_record.storage_key}"
            
            # 5. Update database
            await self.duma_file_repo.update_file_status_and_urls(
                file_id, "completed", s3_url=s3_url
            )
            
            # 6. Return file details
            updated_file = await self.duma_file_repo.get_file(file_id)
            
            return FileResponse(
                id=updated_file.id,
                dumapod_id=updated_file.dumapod_id,
                user_id=updated_file.user_id,
                file_name=updated_file.file_name,
                file_type=updated_file.file_type,
                file_size=updated_file.file_size,
                upload_status=updated_file.upload_status,
                upload_progress=100,
                s3_url=updated_file.s3_url,
                wasabi_url=updated_file.wasabi_url,
                oracle_url=updated_file.oracle_url,
                created_at=updated_file.created_at
            )
            
        except Exception as e:
            logger.error(f"Failed to complete multipart upload: {e}")
            await self.duma_file_repo.update_file_status_and_urls(
                file_id, "failed", failed_reason=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to complete multipart upload: {str(e)}"
            )

    async def abort_multipart_upload(
        self,
        file_id: int,
        user_id: int,
        upload_id: str
    ):
        """Abort multipart upload."""
        # 1. Get file record
        file_record = await self.duma_file_repo.get_by_user_and_id(user_id, file_id)
        
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        if file_record.multipart_upload_id != upload_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid upload ID"
            )
        
        # 2. Get DumaPod info
        dumapod = await self.dumapod_service.get_dumapod(file_record.dumapod_id)
        if isinstance(dumapod, dict):
            primary_storage = dumapod.get("primary_storage")
        else:
            primary_storage = dumapod.primary_storage
        
        # 3. Abort multipart upload in S3
        try:
            provider_value = primary_storage.value if hasattr(primary_storage, 'value') else primary_storage
            
            await self.storage_repo.abort_multipart_upload(
                key=file_record.storage_key,
                upload_id=upload_id,
                provider=provider_value
            )
            
            # 4. Update database
            await self.duma_file_repo.update_file_status_and_urls(
                file_id, "failed", failed_reason="Upload aborted by user"
            )
            
            return {"message": "Multipart upload aborted successfully"}
            
        except Exception as e:
            logger.error(f"Failed to abort multipart upload: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to abort multipart upload: {str(e)}"
            )
