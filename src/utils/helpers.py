"""Helper functions for common operations."""

import hashlib
import secrets
from datetime import datetime
from typing import Optional


def bytes_to_gb(bytes_size: int) -> float:
    """Convert bytes to gigabytes."""
    return bytes_size / (1024 ** 3)


def gb_to_bytes(gb_size: float) -> int:
    """Convert gigabytes to bytes."""
    return int(gb_size * (1024 ** 3))


def generate_s3_key(user_id: int, filename: str, prefix: Optional[str] = None) -> str:
    """
    Generate S3-compatible storage key.
    Format: [prefix/]user_id/YYYY/MM/DD/random_hash/filename
    """
    now = datetime.utcnow()
    random_hash = secrets.token_hex(8)
    date_path = f"{now.year}/{now.month:02d}/{now.day:02d}"

    if prefix:
        return f"{prefix}/{user_id}/{date_path}/{random_hash}/{filename}"
    return f"{user_id}/{date_path}/{random_hash}/{filename}"


def generate_file_hash(content: bytes) -> str:
    """Generate SHA-256 hash of file content."""
    return hashlib.sha256(content).hexdigest()


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    # Remove path components and dangerous characters
    import os
    filename = os.path.basename(filename)
    # Replace spaces and special characters
    filename = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
    return filename[:255]  # Limit length

