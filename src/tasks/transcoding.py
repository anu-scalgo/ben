"""Video transcoding Celery tasks."""

import asyncio
from typing import List
from ..tasks.celery_app import celery_app
from ..repositories.file_repo import FileRepository
from ..repositories.storage_repo import StorageRepository
from ..services.transcoding_service import TranscodingService
from ..config.database import AsyncSessionLocal
from ..utils.constants import UploadStatus


@celery_app.task(name="transcode_video", bind=True, max_retries=3)
def transcode_video(
    self, file_id: int, storage_key: str, storage_provider: str, output_formats: List[str]
) -> dict:
    """
    Transcode video file to multiple formats.
    This is a Celery task that runs asynchronously.
    """
    # Run async code in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async_session = None
    try:
        # Create async session
        async_session = AsyncSessionLocal()

        # Initialize repositories and service
        file_repo = FileRepository(async_session)
        storage_repo = StorageRepository()
        queue_repo = None  # Not needed here
        transcoding_service = TranscodingService(file_repo, storage_repo, queue_repo)

        # Process transcoding
        transcoded_urls = loop.run_until_complete(
            transcoding_service.process_transcode(
                file_id=file_id,
                storage_key=storage_key,
                output_formats=output_formats,
            )
        )

        # Close session
        loop.run_until_complete(async_session.close())

        return {
            "file_id": file_id,
            "status": "completed",
            "transcoded_urls": transcoded_urls,
        }
    except Exception as exc:
        # Update file status to failed
        if async_session:
            try:
                file_repo = FileRepository(async_session)
                loop.run_until_complete(
                    file_repo.update_upload_status(file_id, UploadStatus.FAILED.value)
                )
                loop.run_until_complete(async_session.close())
            except Exception:
                pass

        # Retry task
        raise self.retry(exc=exc, countdown=60)
    finally:
        loop.close()

