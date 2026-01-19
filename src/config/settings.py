"""Application settings using Pydantic Settings."""

from typing import List, Annotated
from pydantic import Field, field_validator, BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_comma_separated_list(v):
    """Parse comma-separated string into list."""
    if isinstance(v, str):
        return [item.strip() for item in v.split(",") if item.strip()]
    if isinstance(v, list):
        return v
    return []


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Dumacle API", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    environment: str = Field(default="development", alias="ENVIRONMENT")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/dumacle",
        alias="DATABASE_URL",
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # Stripe
    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_publishable_key: str = Field(default="", alias="STRIPE_PUBLISHABLE_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")

    # Storage
    storage_provider: str = Field(default="s3", alias="STORAGE_PROVIDER")
    aws_access_key_id: str = Field(default="", alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    s3_bucket_name: str = Field(default="dumacle-storage", alias="S3_BUCKET_NAME")

    # Oracle Cloud Storage
    oracle_access_key: str = Field(default="", alias="ORACLE_ACCESS_KEY")
    oracle_secret_key: str = Field(default="", alias="ORACLE_SECRET_KEY")
    oracle_bucket_name: str = Field(default="", alias="ORACLE_BUCKET_NAME")
    oracle_namespace: str = Field(default="", alias="ORACLE_NAMESPACE")

    # Wasabi
    wasabi_access_key: str = Field(default="", alias="WASABI_ACCESS_KEY")
    wasabi_secret_key: str = Field(default="", alias="WASABI_SECRET_KEY")
    wasabi_bucket_name: str = Field(default="", alias="WASABI_BUCKET_NAME")
    wasabi_endpoint: str = Field(
        default="https://s3.wasabisys.com", alias="WASABI_ENDPOINT"
    )

    # JWT
    jwt_secret_key: str = Field(
        default="your-super-secret-jwt-key-change-in-production",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=30, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # CORS (stored as string, parsed via property)
    allowed_origins_str: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        alias="ALLOWED_ORIGINS",
        exclude=True,  # Don't include in model dump
    )

    @property
    def allowed_origins(self) -> List[str]:
        """Parse allowed origins from comma-separated string."""
        return parse_comma_separated_list(self.allowed_origins_str)

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")

    # File Upload
    max_file_size_mb: int = Field(default=2048, alias="MAX_FILE_SIZE_MB")
    allowed_file_types_str: str = Field(
        default="video/mp4,video/avi,video/mov,video/mkv,application/pdf,image/jpeg,image/png",
        alias="ALLOWED_FILE_TYPES",
        exclude=True,  # Don't include in model dump
    )

    @property
    def allowed_file_types(self) -> List[str]:
        """Parse allowed file types from comma-separated string."""
        return parse_comma_separated_list(self.allowed_file_types_str)

    # FFmpeg
    ffmpeg_path: str = Field(default="/usr/bin/ffmpeg", alias="FFMPEG_PATH")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = Field(default="logs/app.log", alias="LOG_FILE")

    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size from MB to bytes."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic."""
        return self.database_url.replace("+asyncpg", "")


# Global settings instance
settings = Settings()

