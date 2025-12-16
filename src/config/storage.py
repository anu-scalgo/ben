"""Storage configuration for multi-provider support (S3, Oracle, Wasabi)."""

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from typing import Optional
from .settings import settings


def get_storage_client() -> BaseClient:
    """
    Get storage client based on configured provider.
    Returns boto3 client configured for the selected storage provider.
    """
    provider = settings.storage_provider.lower()

    if provider == "s3":
        return boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
            config=Config(signature_version="s3v4"),
        )

    elif provider == "oracle":
        # Oracle Cloud Storage uses S3-compatible API
        return boto3.client(
            "s3",
            aws_access_key_id=settings.oracle_access_key,
            aws_secret_access_key=settings.oracle_secret_key,
            endpoint_url=f"https://{settings.oracle_namespace}.compat.objectstorage.{settings.aws_region}.oraclecloud.com",
            config=Config(signature_version="s3v4"),
        )

    elif provider == "wasabi":
        return boto3.client(
            "s3",
            aws_access_key_id=settings.wasabi_access_key,
            aws_secret_access_key=settings.wasabi_secret_key,
            endpoint_url=settings.wasabi_endpoint,
            region_name=settings.aws_region,
            config=Config(signature_version="s3v4"),
        )

    else:
        raise ValueError(f"Unsupported storage provider: {provider}")


def get_bucket_name() -> str:
    """Get bucket name for the configured storage provider."""
    provider = settings.storage_provider.lower()

    if provider == "s3":
        return settings.s3_bucket_name
    elif provider == "oracle":
        return settings.oracle_bucket_name
    elif provider == "wasabi":
        return settings.wasabi_bucket_name
    else:
        raise ValueError(f"Unsupported storage provider: {provider}")

