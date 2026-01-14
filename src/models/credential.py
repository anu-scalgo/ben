"""Storage Credential model definition."""

from sqlalchemy import Integer, String, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..config.database import Base
from .dumapod import StorageProvider, DumaPod


class StorageCredential(Base):
    """Storage Credential database model."""

    __tablename__ = "storage_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dumapod_id: Mapped[int] = mapped_column(Integer, ForeignKey("dumapods.id"), nullable=False)
    provider: Mapped[StorageProvider] = mapped_column(Enum(StorageProvider), nullable=False)
    
    # Common fields
    access_key: Mapped[str] = mapped_column(String, nullable=False)
    secret_key: Mapped[str] = mapped_column(String, nullable=False)
    bucket_name: Mapped[str] = mapped_column(String, nullable=False)
    
    # Provider-specific fields (nullable as not all providers need all fields)
    endpoint_url: Mapped[str | None] = mapped_column(String, nullable=True)
    region: Mapped[str | None] = mapped_column(String, nullable=True)
    namespace: Mapped[str | None] = mapped_column(String, nullable=True) # For Oracle

    dumapod = relationship("DumaPod", back_populates="credentials")
