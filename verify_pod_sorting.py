
import asyncio
import httpx
import sys

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
        print("\n2. Getting currently available pods...")
        response = await client.get("/dumapods", headers=headers)
        if response.status_code != 200:
             print(f"Failed to list pods: {response.text}")
             return

        pods = response.json()
        print(f"Found {len(pods)} pods.")
        
        if not pods:
             print("No pods to check sorting. Creating two pods...")
             # Create 2 pods a bit apart? Database timestamp resolution is fine.
             resp1 = await client.post("/dumapods", json={"name": "SortPod1"}, headers=headers)
             await asyncio.sleep(1)
             resp2 = await client.post("/dumapods", json={"name": "SortPod2"}, headers=headers)
             
             response = await client.get("/dumapods", headers=headers)
             pods = response.json()
        
        if len(pods) < 2:
             print("Not enough pods to verify sorting.")
             return
             
        print("\n3. Verifying Order (Newest First)...")
        # Check if created_at of [0] > [1]
        
        # We need created_at. The response model includes created_at.
        # Format: "2024-01-01T12:00:00"
        from datetime import datetime
        
        sorted_correctly = True
        for i in range(len(pods) - 1):
            pod_a = pods[i]
            pod_b = pods[i+1]
            
            # Simple string comparison works for ISO format usually, but let's parse to be safe if needed.
            # actually string compare is fine for "YYYY-MM-DDTHH:MM:SS"
            
            date_a = pod_a['created_at']
            date_b = pod_b['created_at']
            
            print(f"Compare: {pod_a['name']} ({date_a}) vs {pod_b['name']} ({date_b})")
            
            if date_a < date_b:
                print("  ✗ FAILURE: Older pod found before newer pod.")
                sorted_correctly = False
                break
        
        if sorted_correctly:
            print("✓ SUCCESS: Pods are sorted by newest first.")

        # Clean up created pods if any
        for pod in pods:
             if pod['name'] in ["SortPod1", "SortPod2"]:
                  await client.delete(f"/dumapods/{pod['id']}", headers=headers)

if __name__ == "__main__":
    asyncio.run(main())
