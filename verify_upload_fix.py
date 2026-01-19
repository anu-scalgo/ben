import asyncio
import httpx
from src.models.user import User
from src.schemas.dumapod import DumaPodCreate

# Configuration
BASE_URL = "http://localhost:8002"

async def main():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # 1. Login
        email = "testuser_upload@example.com"
        password = "password123"
        
        # Try to login
        response = await client.post("/auth/login", json={"email": email, "password": password})
        
        if response.status_code != 200:
             # Try register again if deleted or something (unlikely)
             await client.post("/auth/register", json={
                "email": email,
                "password": password,
                "full_name": "Upload Tester"
            })
             response = await client.post("/auth/login", json={"email": email, "password": password})
        
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return
            
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Logged in.")

        # 2. Skip Pod creation because of 403
        pod_id = 999999 # Dummy ID

        # 3. Upload File
        print("Uploading file to dummy pod...")
        files = {'file': ('test.txt', b'Hello, world!', 'text/plain')}
        data = {'dumapod_id': str(pod_id), 'description': 'Test file'}
        
        upload_headers = headers.copy()
        
        res = await client.post("/files/upload", headers=upload_headers, files=files, data=data)
        print(f"Upload Response: {res.status_code} - {res.text}")
        
        if "Unsupported storage provider" in res.text:
             print("Verification Failed: Still getting Unsupported Storage Provider error")
        elif res.status_code == 500:
             print("Verification Failed: 500 Internal Server Error (Unknown cause)")
        else:
             print("Verification Passed: Error changed (likely means Provider check passed, now failing on something else e.g. 404/403/400 logic downstream)")

if __name__ == "__main__":
    asyncio.run(main())
