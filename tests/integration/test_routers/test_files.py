"""Integration tests for file routes."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.integration
async def test_upload_file_requires_auth(client: AsyncClient):
    """Test that file upload requires authentication."""
    response = await client.post("/files/upload")
    assert response.status_code == 401  # Unauthorized


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_files_requires_auth(client: AsyncClient):
    """Test that listing files requires authentication."""
    response = await client.get("/files")
    assert response.status_code == 401  # Unauthorized


@pytest.mark.asyncio
@pytest.mark.integration
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

