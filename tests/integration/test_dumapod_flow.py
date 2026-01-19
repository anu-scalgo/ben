
import pytest
from httpx import AsyncClient
from src.models.user import UserRole, User
from src.models.dumapod import StorageProvider
from datetime import datetime
from zoneinfo import ZoneInfo

@pytest.mark.asyncio
async def test_dumapod_flow(client: AsyncClient, db_session):
    # 1. Setup Users (Admin and Enduser)
    admin = User(
        email="admin_dp@example.com",
        hashed_password="$2b$12$ILJYY74cVhd.OHt9Ar/Pre6BumikOvwNqgrEz7G1PSuVNRqW0MwP2", # "secret123"
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
        created_at=datetime.now(ZoneInfo("UTC")),
        updated_at=datetime.now(ZoneInfo("UTC"))
    )
    enduser = User(
        email="user_dp@example.com",
        hashed_password="$2b$12$ILJYY74cVhd.OHt9Ar/Pre6BumikOvwNqgrEz7G1PSuVNRqW0MwP2", # "secret123"
        full_name="End User",
        role=UserRole.ENDUSER,
        is_active=True,
        created_at=datetime.now(ZoneInfo("UTC")),
        updated_at=datetime.now(ZoneInfo("UTC"))
    )
    db_session.add(admin)
    db_session.add(enduser)
    await db_session.commit()

    # Login as Admin
    resp = await client.post("/auth/login", json={"email": "admin_dp@example.com", "password": "secret123"})
    admin_token = resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Login as Enduser
    resp = await client.post("/auth/login", json={"email": "user_dp@example.com", "password": "secret123"})
    user_token = resp.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 2. Admin creates Valid Duma Pod
    pod_data = {
        "name": "Gold Plan",
        "storage_capacity_gb": 1000,
        "enable_s3": True,
        "enable_wasabi": False,
        "enable_oracle_os": False,
        "primary_storage": "aws_s3",
        "secondary_storage": None,
        "amount_in_usd": 99.99,
        "is_active": True
    }
    response = await client.post("/dumapods", json=pod_data, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Gold Plan"
    assert data["primary_storage"] == "aws_s3"
    pod_id = data["id"]
    
    # 3. Check Validation Error (Enable S3=False but Primary=S3)
    invalid_data = pod_data.copy()
    invalid_data["name"] = "Invalid Plan"
    invalid_data["enable_s3"] = False
    response = await client.post("/dumapods", json=invalid_data, headers=admin_headers)
    assert response.status_code == 400
    assert "Amazon S3 must be enabled" in response.json()["detail"]
    
    # 4. Check Validation Error (Primary == Secondary)
    invalid_data = pod_data.copy()
    invalid_data["name"] = "Invalid Plan 2"
    invalid_data["secondary_storage"] = "aws_s3"
    response = await client.post("/dumapods", json=invalid_data, headers=admin_headers)
    assert response.status_code == 400
    assert "Secondary storage cannot be the same" in response.json()["detail"]

    # 5. List Pods
    response = await client.get("/dumapods", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1
    
    # 6. Enduser tries to create (Should Fail)
    response = await client.post("/dumapods", json=pod_data, headers=user_headers)
    assert response.status_code == 403
    
    # 7. Update Pod
    update_data = {"name": "Gold Plan Updated"}
    response = await client.patch(f"/dumapods/{pod_id}", json=update_data, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Gold Plan Updated"
    
    # 8. Delete Pod
    response = await client.delete(f"/dumapods/{pod_id}", headers=admin_headers)
    assert response.status_code == 204
    
    # Verify soft delete (is_active=False via GET)
    # The GET endpoint does not currently filter by is_active (unless we implemented it?) 
    # Let's check get_dumapod
    response = await client.get(f"/dumapods/{pod_id}", headers=admin_headers)
    assert response.status_code == 200 # Should still exist
    assert response.json()["is_active"] == False
