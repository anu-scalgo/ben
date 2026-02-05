
import asyncio
import httpx
import sys
import json

# Configuration
BASE_URL = "http://localhost:8002"
EMAIL = "admin@example.com"
PASSWORD = "admin123456"

async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Login
        print("1. Logging in...")
        response = await client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return

        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Get All Pods
        print("\n2. Getting pods to check connection status...")
        response = await client.get("/dumapods", headers=headers)
        if response.status_code != 200:
             print(f"Failed to list pods: {response.text}")
             return

        pods = response.json()
        print(f"Found {len(pods)} pods.")
        
        if pods:
            pod = pods[0]
            print(f"Checking Pod: {pod.get('name')}")
            print(f"Connection Status: {json.dumps(pod.get('connection_status'), indent=2)}")
            
            if 'connection_status' in pod:
                print("✓ connection_status field is present.")
                if isinstance(pod['connection_status'], dict):
                     print("✓ connection_status is a dictionary.")
                else:
                     print("✗ connection_status is NOT a dictionary.")
            else:
                print("✗ connection_status field is MISSING.")
        else:
            print("No pods found. Create one first.")

if __name__ == "__main__":
    asyncio.run(main())
