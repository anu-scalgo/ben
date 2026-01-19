import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from config.settings import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

async def add_progress_column():
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        print("Checking if upload_progress column exists...")
        # efficient check
        # But for simplicity in this migration script, just try adding it and catch error or check generic
        # Let's check information_schema
        
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='duma_stored_files' AND column_name='upload_progress'"
        ))
        if result.scalar():
            print("Column upload_progress already exists. Skipping.")
        else:
            print("Adding upload_progress column...")
            await conn.execute(text("ALTER TABLE duma_stored_files ADD COLUMN upload_progress INTEGER DEFAULT 0 NOT NULL"))
            print("Column added successfully.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_progress_column())
