"""DumaStoredFile model definition."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, String, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..config.database import Base


class DumaStoredFile(Base):
    """Model for files stored in DumaPods."""

    __tablename__ = "duma_stored_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dumapod_id: Mapped[int] = mapped_column(Integer, ForeignKey("dumapods.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False)  # content_type
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # S3 key/path
    upload_status: Mapped[str] = mapped_column(String, default="pending", nullable=True)
    upload_progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Store URLs/Links for each provider
    s3_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    wasabi_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    oracle_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    # Relationships
    dumapod = relationship("DumaPod", backref="stored_files")
    user = relationship("User", backref="duma_stored_files")
