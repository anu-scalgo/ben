import asyncio
import httpx
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from src.config.database import engine, Base
from src.models.user import User, UserRole
from src.models.dumapod import DumaPod, StorageProvider
from src.models.credential import StorageCredential
from src.models.duma_stored_file import DumaStoredFile
from src.core.security import get_password_hash
from src.repositories.duma_stored_file_repo import DumaStoredFileRepository

async def verify_failed_exclusion():
    # 1. Setup Database
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        # Create test user
        stmt = select(User).where(User.email == "failed_test@example.com")
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                email="failed_test@example.com", 
                hashed_password=get_password_hash("testpassword123"),
                full_name="Failed Test",
                role=UserRole.SUPERADMIN
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            # Update password to ensure it matches and is valid length
            user.hashed_password = get_password_hash("testpassword123")
            session.add(user)
            await session.commit()
            await session.refresh(user)

        # Create test pod
        stmt = select(DumaPod).where(DumaPod.name == "FailedTestPod")
        result = await session.execute(stmt)
        pod = result.scalar_one_or_none()
        
        if not pod:
            pod = DumaPod(
                name="FailedTestPod",
                storage_capacity_gb=10,
                created_by=user.id,
                primary_storage=StorageProvider.AWS_S3,
                amount_in_usd=0.0
            )
            session.add(pod)
            await session.commit()
            await session.refresh(pod)
        
        # 2. Add files (Success and Failed)
        repo = DumaStoredFileRepository(session)
        
        # Success file (1GB)
        await repo.create_file_record(
            dumapod_id=pod.id,
            user_id=user.id,
            file_name="success.bin",
            file_type="application/octet-stream",
            file_size=1024**3, # 1GB
            upload_status="completed"
        )
        
        # Failed file (5GB)
        await repo.create_file_record(
            dumapod_id=pod.id,
            user_id=user.id,
            file_name="failed.bin",
            file_type="application/octet-stream",
            file_size=5 * 1024**3, # 5GB
            upload_status="failed"
        )
        
        # Pending file (Should be counted? Usually yes, until it fails)
        # Let's check pending to be sure behavior is as expected (included)
        await repo.create_file_record(
            dumapod_id=pod.id,
            user_id=user.id,
            file_name="pending.bin",
            file_type="application/octet-stream",
            file_size=1024**3, # 1GB
            upload_status="pending"
        )

    # 3. Check API
    async with httpx.AsyncClient(base_url="http://localhost:8002") as client:
        # Login
        response = await client.post("/auth/login", json={"email": "failed_test@example.com", "password": "testpassword123"})
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return
            
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get usage
        response = await client.get(f"/users/usage?user_id={user.id}", headers=headers)
        data = response.json()
        
        pod_usage = data[0]["pods"][0]
        print(f"Pod Usage: {pod_usage}")
        
        # Expected: 2GB used (1GB success + 1GB pending), 5GB failed ignored.
        # If pending is excluded, it would be 1GB. Current logic only excludes 'failed'.
        
        expected_used = 2.0
        actual_used = pod_usage["used_storage_gb"]
        
        if actual_used == expected_used:
            print("SUCCESS: Failed file excluded correctly.")
        else:
            print(f"FAILURE: Expected {expected_used} GB, got {actual_used} GB")

if __name__ == "__main__":
    from sqlalchemy.ext.asyncio import AsyncSession
    asyncio.run(verify_failed_exclusion())
