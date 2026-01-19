
import pytest
from httpx import AsyncClient
from src.models.user import UserRole

@pytest.mark.asyncio
async def test_user_management_flow(client: AsyncClient):
    # 1. Register a new user (default role: ENDUSER)
    register_data = {
        "email": "enduser@example.com",
        "password": "password123",
        "full_name": "End User"
    }
    response = await client.post("/auth/register", json=register_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == register_data["email"]
    assert data["role"] == UserRole.ENDUSER.value
    user_id = data["id"]

    # 2. Login as Enduser
    login_data = {
        "email": "enduser@example.com",
        "password": "password123"
    }
    response = await client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    token_data = response.json()
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 3. Try to list users (should fail - 403)
    response = await client.get("/users", headers=headers)
    assert response.status_code == 403

    # 4. Create a Superadmin user (Mocking this by creating via API won't work without token, 
    # so we need to hack: Register then manually update role in DB? 
    # Or for testing purpose, let's just assume we can create one via DB fixture, 
    # but here we are integration testing via API.
    # We can use the 'register' endpoint to create another user, 
    # then maybe use a backdoor or just rely on the fact that we can't create superadmin via API initially.
    # But we need a superadmin to test user management!)
    
    # We will register admin@example.com
    # Then we need to elevate it to SUPERADMIN. 
    # Since we don't have direct DB access easily in this test function (unless we use db_session fixture),
    # we should likely use the db_session fixture (checking conftest).
    # Wait, 'client' fixture overrides get_db with db_session.
    # But how do we access that same session here to modify data?
    # We don't have access to the session object used by the client directly here unless we ask for it again?
    # Actually, we can just request `db_session` fixture in this test function!
    # It adheres to 'function' scope, same as client. 
    pass 

@pytest.mark.asyncio
async def test_admin_flow(client: AsyncClient, db_session):
    from src.models.user import User
    from sqlalchemy import select
    from datetime import datetime
    from zoneinfo import ZoneInfo

    # 1. Create a Superadmin manually in DB
    superadmin = User(
        email="superadmin@example.com",
        hashed_password="$2b$12$ILJYY74cVhd.OHt9Ar/Pre6BumikOvwNqgrEz7G1PSuVNRqW0MwP2", # "secret123"
        full_name="Super Admin",
        role=UserRole.SUPERADMIN,
        is_active=True,
        created_at=datetime.now(ZoneInfo("UTC")),
        updated_at=datetime.now(ZoneInfo("UTC"))
    )
    db_session.add(superadmin)
    await db_session.commit()
    
    # Login as Superadmin
    login_data = {
        "email": "superadmin@example.com",
        "password": "secret123"
    }
    response = await client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 2. List users (should be allowed)
    response = await client.get("/users", headers=headers)
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 1
    
    # 3. Create an ADMIN user
    admin_data = {
        "email": "admin@example.com",
        "password": "password123",
        "full_name": "Admin User",
        "role": "admin"
    }
    response = await client.post("/users", json=admin_data, headers=headers)
    assert response.status_code == 201
    assert response.json()["role"] == "admin"
    
    # 4. Verify Admin can login
    response = await client.post("/auth/login", json={"email": "admin@example.com", "password": "password123"})
    assert response.status_code == 200
    admin_token = response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 5. Admin lists users
    response = await client.get("/users", headers=admin_headers)
    assert response.status_code == 200
