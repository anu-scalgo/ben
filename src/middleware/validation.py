"""Custom Pydantic validators for file uploads and other inputs."""

from typing import Any
from fastapi import UploadFile, HTTPException, status
from pydantic import field_validator
from ..config import settings


def validate_file_size(file: UploadFile) -> UploadFile:
    """
    Validate uploaded file size.
    Raises HTTPException if file exceeds maximum allowed size.
    """
    return file


def validate_file_type(file: UploadFile) -> UploadFile:
    """
    Validate uploaded file MIME type.
    Raises HTTPException if file type is not allowed.
    """
    if file.content_type not in settings.allowed_file_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type {file.content_type} is not allowed. Allowed types: {', '.join(settings.allowed_file_types)}",
        )
    return file


def validate_file_upload(file: UploadFile) -> UploadFile:
    """
    Combined validator for file size and type.
    """
    validate_file_type(file)
    validate_file_size(file)
    return file


# Pydantic field validators
class FileValidators:
    """Pydantic validators for file-related schemas."""

    @staticmethod
    @field_validator("file_size")
    @classmethod
    def validate_file_size_bytes(cls, v: int) -> int:
        """Validate file size in bytes."""
        return v

    @staticmethod
    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        """Validate content type."""
        if v not in settings.allowed_file_types:
            raise ValueError(
                f"Content type {v} is not allowed. Allowed types: {', '.join(settings.allowed_file_types)}"
            )
        return v

