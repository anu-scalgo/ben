
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
            sys.exit(1)
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create a Pod (S3 Enabled)
        print("\n2. Creating a Pod to test connection check...")
        pod_data = {
            "name": "check_conn_api_test",
            "storage_capacity_gb": 100,
            "enable_s3": True,
            "primary_storage": "aws_s3"
        }
        response = await client.post("/dumapods", json=pod_data, headers=headers)
        if response.status_code != 201:
             # If exists, get it?
             if response.status_code == 400 and "already exists" in response.text:
                 print("Pod already exists, listing to find ID...")
                 list_resp = await client.get("/dumapods", headers=headers)
                 pods = list_resp.json()
                 pod_id = next((p['id'] for p in pods if p['name'] == "check_conn_api_test"), None)
             else:
                print(f"Create failed: {response.text}")
                sys.exit(1)
        else:
            pod_id = response.json()["id"]
        
        print(f"Using Pod ID: {pod_id}")

        # 3. Call Check Connection API
        print(f"\n3. Calling POST /dumapods/{pod_id}/check-connection...")
        response = await client.post(f"/dumapods/{pod_id}/check-connection", headers=headers)
        
        if response.status_code == 200:
            status = response.json()
            print("✓ API Call Successful")
            print(f"Returned Status: {status}")
            
            if "aws_s3" in status and status["aws_s3"] is True:
                print("✓ aws_s3 status is True (Expected)")
            else:
                print("✗ aws_s3 status is missing or False (Unexpected for this test)")
                sys.exit(1)
        else:
            print(f"✗ API Call Failed: {response.status_code} - {response.text}")
            sys.exit(1)

        # 4. Clean up
        print(f"\n4. Deleting Pod {pod_id}...")
        await client.delete(f"/dumapods/{pod_id}", headers=headers)

if __name__ == "__main__":
    asyncio.run(main())
