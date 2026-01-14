"""DumaPod model definition."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, String, Integer, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..config.database import Base


class StorageProvider(str, enum.Enum):
    """Storage provider types."""

    AWS_S3 = "aws_s3"
    WASABI = "wasabi"
    ORACLE_OS = "oracle_object_storage"


class DumaPod(Base):
    """DumaPod (Storage Plan) database model."""

    __tablename__ = "dumapods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    storage_capacity_gb: Mapped[int] = mapped_column(Integer, nullable=False)
    
    enable_s3: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enable_wasabi: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enable_oracle_os: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    primary_storage: Mapped[StorageProvider] = mapped_column(
        Enum(StorageProvider), nullable=False
    )
    secondary_storage: Mapped[Optional[StorageProvider]] = mapped_column(
        Enum(StorageProvider), nullable=True
    )
    
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    amount_in_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    creator = relationship("User", backref="created_dumapods")
