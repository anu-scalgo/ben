
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
        
        # 2. Create Pod with ONLY Name
        print("\n2. Creating Pod with ONLY Name...")
        pod_name = "Minimal Pod Plan"
        pod_data = {
            "name": pod_name
        }
        
        response = await client.post("/dumapods", json=pod_data, headers=headers)
        
        if response.status_code == 201:
            pod = response.json()
            print(f"✓ Created Pod: ID {pod['id']}")
            print(f"  Name: {pod['name']}")
            print(f"  Storage: {pod.get('storage_capacity_gb')} (Expected: None)")
            print(f"  Price: {pod.get('amount_in_usd')} (Expected: None)")
            
            if pod.get('storage_capacity_gb') is None and pod.get('amount_in_usd') is None:
                 print("  ✓ Optional fields are None as expected!")
            else:
                 print("  ? Optional fields might have defaults or backend logic (check schemas)")
                 
            # Cleanup
            print(f"\n3. Deleting Pod {pod['id']}...")
            await client.delete(f"/dumapods/{pod['id']}", headers=headers)
            
        elif response.status_code == 400 and "already exists" in response.text:
             print("Pod already exists. Please delete 'Minimal Pod Plan' manually.")
        else:
            print(f"Failed to create pod: {response.status_code} - {response.text}")

if __name__ == "__main__":
    asyncio.run(main())
