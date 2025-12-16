"""Deployment script with environment checks."""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings


def check_environment():
    """Check that all required environment variables are set."""
    required_vars = [
        "DATABASE_URL",
        "REDIS_URL",
        "JWT_SECRET_KEY",
    ]

    missing_vars = []
    for var in required_vars:
        env_value = getattr(settings, var.lower(), None)
        if not env_value or env_value == "":
            missing_vars.append(var)

    if missing_vars:
        print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    print("✓ All required environment variables are set")


def check_database_connection():
    """Check database connection."""
    try:
        import asyncio
        from src.config.database import engine

        async def test_connection():
            async with engine.begin() as conn:
                await conn.execute("SELECT 1")

        asyncio.run(test_connection())
        print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        sys.exit(1)


def check_redis_connection():
    """Check Redis connection."""
    try:
        from src.config.redis import redis_client
        redis_client.ping()
        print("✓ Redis connection successful")
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        sys.exit(1)


def main():
    """Run deployment checks."""
    print("Running deployment checks...")
    print("-" * 50)

    check_environment()
    check_database_connection()
    check_redis_connection()

    print("-" * 50)
    print("✓ All checks passed! Ready for deployment.")


if __name__ == "__main__":
    main()

