
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
        
        # 2. Create Pod with Description
        print("\n2. Creating Pod with Description...")
        pod_data = {
            "name": "Descriptive Pod Plan",
            "storage_capacity_gb": 100,
            "enable_s3": True,
            "primary_storage": "aws_s3",
            "amount_in_usd": 10.0,
            "pod_description": "This is a plan with a detailed description."
        }
        
        response = await client.post("/dumapods", json=pod_data, headers=headers)
        
        if response.status_code == 201:
            pod = response.json()
            print(f"✓ Created Pod: ID {pod['id']}")
            print(f"  Description: {pod.get('pod_description')}")
            
            if pod.get('pod_description') == pod_data['pod_description']:
                 print("  ✓ Description matches!")
            else:
                 print("  ✗ Description mismatch!")
                 
            pod_id = pod['id']

            # 3. Update Pod Description
            print(f"\n3. Updating Pod {pod_id} Description...")
            update_data = {"pod_description": "Updated description for this pod."}
            response = await client.patch(f"/dumapods/{pod_id}", json=update_data, headers=headers)
            
            if response.status_code == 200:
                updated_pod = response.json()
                print(f"✓ Updated Description: {updated_pod.get('pod_description')}")
                if updated_pod.get('pod_description') == update_data['pod_description']:
                     print("  ✓ Description updated successfully!")
                else:
                     print("  ✗ Update failed verification!")
            else:
                 print(f"Failed to update: {response.status_code} - {response.text}")

            # Cleanup
            print(f"\n4. Deleting Pod {pod_id}...")
            await client.delete(f"/dumapods/{pod_id}", headers=headers)
            
        elif response.status_code == 400 and "already exists" in response.text:
             print("Pod already exists. Please delete 'Descriptive Pod Plan' manually or run again (if clean).")
        else:
            print(f"Failed to create pod: {response.status_code} - {response.text}")

if __name__ == "__main__":
    asyncio.run(main())
