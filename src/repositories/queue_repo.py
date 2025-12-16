"""Queue repository for Celery task management."""

from typing import Any, Dict


class QueueRepository:
    """Repository for queue operations using Celery."""

    @staticmethod
    def enqueue_transcode(
        file_id: int,
        storage_key: str,
        storage_provider: str,
        output_formats: list[str],
    ) -> Dict[str, Any]:
        """
        Enqueue video transcoding task.
        Args:
            file_id: File ID
            storage_key: Storage key of source file
            storage_provider: Storage provider name
            output_formats: List of output formats (e.g., ['mp4', 'webm'])
        Returns:
            Task ID and status
        """
        # Import here to avoid circular imports
        from ..tasks.transcoding import transcode_video

        task = transcode_video.delay(
            file_id=file_id,
            storage_key=storage_key,
            storage_provider=storage_provider,
            output_formats=output_formats,
        )
        return {
            "task_id": task.id,
            "status": "queued",
        }

    @staticmethod
    def get_task_status(task_id: str) -> Dict[str, Any]:
        """Get Celery task status."""
        # Import here to avoid circular imports
        from ..tasks.celery_app import celery_app

        task = celery_app.AsyncResult(task_id)
        return {
            "task_id": task_id,
            "status": task.status,
            "result": task.result if task.ready() else None,
        }

