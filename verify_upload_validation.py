
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

        # 2. Create Pod with Invalid Credentials (simulate connection failure)
        print("\n2. Creating Pod with Invalid Credentials (valid capacity)...")
        pod_data_conn_fail = {
            "name": "conn_fail_pod",
            "storage_capacity_gb": 10,
            "enable_s3": True,
            "primary_storage": "aws_s3",
            "use_custom_s3": True
            # No credentials added, or we should add invalid ones.
            # If use_custom_s3 is True, and we don't add credentials, check_connectivity might fail or return False.
            # DumaPodService.create_dumapod -> _calculate_connection_status -> check(custom=True)
            # if no credentials, returns False.
        }
        
        # We need to be careful: create_dumapod -> _validate_storage_config might pass
        # But _calculate_connection_status will run.
        # However, update/create might Enforce validation?
        # Service: "if pod_data.use_custom_s3 is True: await self._validate_credential_connectivity(pod_id, StorageProvider.AWS_S3)"
        # This validation runs on UPDATE. Does it run on CREATE?
        # create_dumapod -> _calculate_connection_status only. It doesn't call _validate_credential_connectivity explicitly for custom?
        # Let's check create_dumapod in service.
        
        # Actually create_dumapod calls _calculate_connection_status.
        # If use_custom_s3=True but no credentials, _calculate_connection_status returns False.
        # So connection_status = {'aws_s3': False}.
        
        # But wait, to use custom S3, we usually need to add credentials via separate API *after* creating pod?
        # Or does Create accept credentials? Schema says No.
        # So usually: Create Pod (use_custom=False) -> Add Creds -> Update Pod (use_custom=True).
        
        # Let's try: Create Pod (default S3). Connection check will likely fail if env vars are not set for default?
        # Or assuming default works.
        
        # Best way to ensure FAILURE:
        # Create Pod (enable_s3=True). 
        # If default creds work, status is True.
        # How to make it False?
        # Maybe use a provider that definitely fails or isn't configured?
        # Oracle?
        
        pod_data_oracle = {
            "name": "oracle_fail_pod",
            "storage_capacity_gb": 10,
            "enable_s3": False,
            "enable_oracle_os": True,
            "primary_storage": "oracle_object_storage"
        }
        
        resp = await client.post("/dumapods", json=pod_data_oracle, headers=headers)
        if resp.status_code == 201:
             pod_id = resp.json()["id"]
             print(f"Created Pod {pod_id} with Oracle (expected to fail connection)")
        elif resp.status_code == 400 and "already exists" in resp.text:
             list_resp = await client.get("/dumapods", headers=headers)
             pod_id = next((p['id'] for p in list_resp.json() if p['name'] == "oracle_fail_pod"), None)
        else:
            print(f"Failed to create pod: {resp.text}")
            sys.exit(1)
            
        print(f"Testing Upload on Pod {pod_id} (Expected Connection Failure)...")
        
        init_data = {
            "dumapod_id": pod_id,
            "filename": "test.jpg",
            "content_type": "image/jpeg",
            "file_size": 1024,
            "description": "test"
        }
        resp = await client.post("/files/initiate-upload", json=init_data, headers=headers)
        
        print(f"Response: {resp.status_code} - {resp.text}")
        
        if resp.status_code == 400 and ("no active storage connections" in resp.text.lower() or "no enabled storage provider is connected" in resp.text.lower()):
            print("✓ Correctly rejected upload for pod with no active connection.")
        else:
            print(f"✗ Failed checking connection validation. Status: {resp.status_code}, Body: {resp.text}")
            
        # Clean up
        await client.delete(f"/dumapods/{pod_id}", headers=headers)

if __name__ == "__main__":
    asyncio.run(main())
