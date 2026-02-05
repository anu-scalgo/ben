
import asyncio
import httpx
import sys

# Configuration
BASE_URL = "http://localhost:8002"
EMAIL = "admin@example.com"
PASSWORD = "admin123456"

async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Login
        print("1. Logging in...")
        response = await client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return

        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Create Pod 
        print("\n2. Creating Pod 'Unique Pod'...")
        pod_name = "Unique Pod"
        
        # Ensure it doesn't exist
        # List and delete if present?
        # Just try create.
        
        response = await client.post("/dumapods", json={"name": pod_name}, headers=headers)
        if response.status_code == 201:
             print("✓ Created first time.")
             pod_id = response.json()['id']
        elif response.status_code == 400:
             print("Pod exists, that's fine for this test.")
        else:
             print(f"Failed to create: {response.status_code} - {response.text}")
             return

        # 3. Try Create Duplicate
        print("\n3. Creating Duplicate Pod 'Unique Pod'...")
        response = await client.post("/dumapods", json={"name": pod_name}, headers=headers)
        
        print(f"Response: {response.status_code}")
        print(f"Body: {response.text}")
        
        if response.status_code == 400 and "already exists" in response.text:
            print("✓ SUCCESS: Got 400 Bad Request with friendly message.")
        elif response.status_code == 500:
            print("✗ FAILURE: Got 500 Internal Server Error.")
        else:
            print(f"✗ UNEXPECTED: {response.status_code}")

        # Cleanup
        if 'pod_id' in locals():
            await client.delete(f"/dumapods/{pod_id}", headers=headers)

if __name__ == "__main__":
    asyncio.run(main())
