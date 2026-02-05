
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
        print("\n2. Creating Pod with ONLY Name to check Defaults...")
        pod_name = "Default Values Pod"
        
        # Cleanup first if exists
        try:
            # Try to delete if it exists (we don't have get_by_name exposed in API easily without list loop)
            # Actually we can use our new behavior: create and check for 400
            pass
        except:
             pass

        response = await client.post("/dumapods", json={"name": pod_name}, headers=headers)
        
        if response.status_code == 400:
             print("Pod exists, trying to delete first via get list...")
             list_resp = await client.get("/dumapods", headers=headers)
             for pod in list_resp.json():
                  if pod['name'] == pod_name:
                       await client.delete(f"/dumapods/{pod['id']}", headers=headers)
                       print(f"Deleted existing pod {pod['id']}")
             # Try create again
             response = await client.post("/dumapods", json={"name": pod_name}, headers=headers)

        if response.status_code == 201:
            pod = response.json()
            print(f"✓ Created Pod: ID {pod['id']}")
            
            # Check Defaults
            print(f"  enable_s3: {pod.get('enable_s3')} (Expected: True)")
            print(f"  primary_storage: {pod.get('primary_storage')} (Expected: aws_s3)")
            print(f"  enable_wasabi: {pod.get('enable_wasabi')} (Expected: False)")
            
            if pod.get('enable_s3') is True and pod.get('primary_storage') == 'aws_s3':
                 print("  ✓ Defaults are correct!")
            else:
                 print("  ✗ Defaults are INCORRECT!")

            # Cleanup
            print(f"\n3. Deleting Pod {pod['id']}...")
            await client.delete(f"/dumapods/{pod['id']}", headers=headers)
            
        else:
            print(f"Failed to create pod: {response.status_code} - {response.text}")

if __name__ == "__main__":
    asyncio.run(main())
