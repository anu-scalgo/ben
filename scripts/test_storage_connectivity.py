import asyncio
import sys
import os

# Ensure src is in python path
sys.path.append(os.getcwd())

from src.repositories.storage_repo import StorageRepository, get_storage_client, get_bucket_name

async def test_storage_connectivity():
    repo = StorageRepository()
    
    providers = ["s3", "oracle", "wasabi"]
    
    print("--- Testing Storage Connectivity ---")
    
    for provider in providers:
        print(f"\nTesting Provider: {provider.upper()}")
        try:
            client = await repo._get_client(provider)
            bucket = await repo._get_bucket(provider)
            endpoint = client.meta.endpoint_url
            print(f"✅ Client initialized successfully")
            print(f"   Endpoint: {endpoint}")
            print(f"   Bucket: {bucket}")
            
        except Exception as e:
            print(f"❌ Failed to initialize client: {e}")

if __name__ == "__main__":
    asyncio.run(test_storage_connectivity())
