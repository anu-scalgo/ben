"""Unit tests for file service."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import UploadFile
from src.services.file_service import FileService
from src.schemas.file import FileResponse


@pytest.mark.asyncio
async def test_handle_upload_success(mock_user, mock_subscription):
    """Test successful file upload."""
    # Mock dependencies
    db = AsyncMock()
    file_repo = MagicMock()
    file_repo.create_file = AsyncMock(return_value={
        "id": 1,
        "user_id": 1,
        "filename": "test.mp4",
        "original_filename": "test.mp4",
        "content_type": "video/mp4",
        "file_size": 1024,
        "storage_key": "1/2024/01/01/abc123/test.mp4",
        "storage_provider": "s3",
        "upload_status": "pending",
        "transcoded_urls": [],
    })

    subscription_repo = MagicMock()
    subscription_repo.get_by_user_id = AsyncMock(return_value=mock_subscription)
    subscription_repo.update_quota = AsyncMock()

    storage_repo = MagicMock()
    storage_repo.upload_file = AsyncMock(return_value="1/2024/01/01/abc123/test.mp4")
    storage_repo.generate_key = MagicMock(return_value="1/2024/01/01/abc123/test.mp4")

    queue_repo = MagicMock()
    queue_repo.enqueue_transcode = MagicMock(return_value={"task_id": "123", "status": "queued"})

    # Create service
    service = FileService(db)
    service.file_repo = file_repo
    service.storage_repo = storage_repo
    service.queue_repo = queue_repo
    service.subscription_repo = subscription_repo

    # Mock file
    file = MagicMock(spec=UploadFile)
    file.filename = "test.mp4"
    file.content_type = "video/mp4"
    file.read = AsyncMock(return_value=b"test content")

    # Test upload
    result = await service.handle_upload(user_id=1, file=file)

    assert isinstance(result, FileResponse)
    assert result.user_id == 1
    assert result.filename == "test.mp4"


@pytest.mark.asyncio
async def test_handle_upload_quota_exceeded(mock_subscription):
    """Test file upload with exceeded quota."""
    db = AsyncMock()
    subscription_repo = MagicMock()
    # Mock subscription with exceeded quota
    mock_subscription["used_storage_gb"] = 9.9
    mock_subscription["storage_limit_gb"] = 10.0
    subscription_repo.get_by_user_id = AsyncMock(return_value=mock_subscription)

    service = FileService(db)
    service.subscription_repo = subscription_repo

    file = MagicMock(spec=UploadFile)
    file.filename = "large.mp4"
    file.content_type = "video/mp4"
    file.read = AsyncMock(return_value=b"x" * (200 * 1024 * 1024))  # 200MB

    with pytest.raises(Exception):  # Would be HTTPException in real implementation
        await service.handle_upload(user_id=1, file=file)

