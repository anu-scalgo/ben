import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from src.config.settings import settings

async def migrate():
    # Use async engine since app is async configured
    engine = create_async_engine(settings.database_url)
    
    async with engine.begin() as conn:
        print("Checking if 'upload_status' column exists in 'duma_stored_files'...")
        # Check if column exists
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='duma_stored_files' AND column_name='upload_status';"
        ))
        if result.scalar():
            print("Column 'upload_status' already exists.")
        else:
            print("Adding 'upload_status' column...")
            await conn.execute(text(
                "ALTER TABLE duma_stored_files ADD COLUMN upload_status VARCHAR DEFAULT 'pending';"
            ))
            print("Column added successfully.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())
