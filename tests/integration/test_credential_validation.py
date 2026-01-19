import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.dumapod import DumaPod, StorageProvider
from src.models.credential import StorageCredential
from src.models.user import User, UserRole
from src.core.security import get_password_hash

# Mock StorageRepository.check_connectivity to avoid real S3 calls
import src.services.dumapod_service

@pytest.fixture
async def mock_connectivity(monkeypatch):
    """Mock storage connectivity check."""
    async def mock_check(self, provider, credentials=None):
        # Fail if access key is "INVALID"
        if credentials and credentials.access_key == "INVALID":
            return False
        return True
    
    from src.repositories.storage_repo import StorageRepository
    monkeypatch.setattr(StorageRepository, "check_connectivity", mock_check)

@pytest.mark.asyncio
async def test_credential_validation_flow(
    client: AsyncClient, 
    db_session: AsyncSession,
    mock_connectivity
):
    # 1. Create Superadmin
    admin_data = {
        "email": "validator@example.com",
        "full_name": "Validator",
        "hashed_password": get_password_hash("secret123"),
        "role": UserRole.SUPERADMIN,
        "is_active": True
    }
    admin = User(**admin_data)
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    
    # Login
    response = await client.post("/auth/login", json={
        "email": "validator@example.com",
        "password": "secret123"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create DumaPod
    pod_payload = {
        "name": "Validation Pod",
        "storage_capacity_gb": 100,
        "enable_s3": True,
        "primary_storage": "aws_s3",
        "amount_in_usd": 10.0
    }
    resp = await client.post("/dumapods", json=pod_payload, headers=headers)
    assert resp.status_code == 201
    pod_id = resp.json()["id"]

    # 3. Try to enable custom S3 without credentials -> Should Fail (400)
    # The service expects a credential to exist before enabling.
    resp = await client.patch(f"/dumapods/{pod_id}", json={"use_custom_s3": True}, headers=headers)
    assert resp.status_code == 400
    assert "No custom credentials found" in resp.json()["detail"]

    # 4. Add INVALID credentials
    cred_payload = {
        "provider": "aws_s3",
        "access_key": "INVALID",
        "secret_key": "secret",
        "bucket_name": "bucket",
        "region": "us-east-1"
    }
    resp = await client.post(f"/dumapods/{pod_id}/credentials", json=cred_payload, headers=headers)
    assert resp.status_code == 201
    
    # 5. Try to enable custom S3 with INVALID creds -> Should Fail (400)
    resp = await client.patch(f"/dumapods/{pod_id}", json={"use_custom_s3": True}, headers=headers)
    assert resp.status_code == 400
    assert "Connectivity check failed" in resp.json()["detail"]

    # 6. Update credentials to VALID
    # (We need credential ID first)
    resp = await client.get(f"/dumapods/{pod_id}/credentials", headers=headers)
    cred_id = resp.json()[0]["id"]
    
    update_payload = {"access_key": "VALID"}
    resp = await client.put(f"/dumapods/{pod_id}/credentials/{cred_id}", json=update_payload, headers=headers)
    assert resp.status_code == 200

    # 7. Try to enable custom S3 with VALID creds -> Should Succeed (200)
    resp = await client.patch(f"/dumapods/{pod_id}", json={"use_custom_s3": True}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["use_custom_s3"] is True
