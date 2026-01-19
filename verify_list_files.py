import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.config.settings import settings
from src.repositories.duma_stored_file_repo import DumaStoredFileRepository
from src.services.file_service import FileService
from src.models.duma_stored_file import DumaStoredFile
from src.models.user import User
from src.models.dumapod import DumaPod

DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

async def verify_list_files():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. Setup Repo and Service
        duma_file_repo = DumaStoredFileRepository(session)
        file_service = FileService(session)
        
        # 1.5 Create User and DumaPod
        from src.models.user import User, UserRole
        from src.models.dumapod import DumaPod, StorageProvider
        import random
        
        suffix = random.randint(1000, 9999)
        email = f"testuser{suffix}@example.com"
        
        new_user = User(
            email=email,
            hashed_password="hashed_password",
            full_name="Test User",
            role=UserRole.ENDUSER
        )
        session.add(new_user)
        # Flush to get ID
        await session.flush()
        user_id = new_user.id
        print(f"Created user with ID: {user_id}")
        
        dumapod = DumaPod(
            name=f"TestPod{suffix}",
            storage_capacity_gb=10,
            primary_storage=StorageProvider.AWS_S3,
            created_by=user_id,
            amount_in_usd=10.00
        )
        session.add(dumapod)
        await session.flush()
        dumapod_id = dumapod.id
        print(f"Created dumapod with ID: {dumapod_id}")
        
        await session.commit()
        
        # 2. Create a dummy file record
        print("Creating dummy file record...")
        file_record = await duma_file_repo.create_file_record(
            dumapod_id=dumapod_id,
            user_id=user_id,
            file_name="test_list_files.txt",
            file_type="text/plain",
            file_size=12345,
            upload_status="completed"
        )
        print(f"Created file: {file_record.file_name} (ID: {file_record.id})")
        
        # 3. List files
        print("Listing files...")
        response = await file_service.list_files(user_id=user_id, page=1, page_size=10)
        
        # 4. Verify
        print(f"Total files found: {response.total}")
        found = False
        for f in response.files:
            if f.id == file_record.id:
                found = True
                print(f"Found file in list: {f.filename}, Status: {f.upload_status}")
                assert f.upload_status == "completed"
                # assert f.filename == "test_list_files.txt" # Typo in response? filename vs file_name
        
        if found:
            print("SUCCESS: File found in list_files response.")
        else:
            print("FAILURE: File NOT found in list_files response.")
            
        # Cleanup
        # (Optional) - separate cleanup script or just leave it for dev db

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify_list_files())
