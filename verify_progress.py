import asyncio
import os
import sys
import time

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import httpx

# Configuration
BASE_URL = "http://localhost:8002"

async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
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

        # 2. Upload File
        # Create a decent sized file to ensure we can catch progress
        # 10MB should be enough to take a second or two
        file_size = 10 * 1024 * 1024 
        file_content = os.urandom(file_size)
        files = {'file': ('large_test.mp4', file_content, 'video/mp4')}
        data = {'dumapod_id': '1', 'description': 'Progress Test file'} # Assuming ID 1 exists
        
        upload_headers = headers.copy()
        
        print("Starting upload...")
        # Note: We can't really track client upload progress with httpx easily in this script without complex streamer
        # But we are testing server-to-cloud progress which happens AFTER this returns 202.
        
        res = await client.post("/files/upload", headers=upload_headers, files=files, data=data)
        print(f"Upload Response: {res.status_code}")
        
        if res.status_code != 202:
            print(f"Expected 202, got {res.status_code}: {res.text}")
            return

        file_id = res.json()["id"]
        print(f"File ID: {file_id}. Monitoring progress...")
        
        # 3. Monitor Progress
        prev_progress = -1
        while True:
            res = await client.get(f"/files/{file_id}", headers=headers)
            if res.status_code != 200:
                print(f"Failed to get file status: {res.status_code}")
                break
                
            details = res.json()
            status = details["upload_status"]
            progress = details.get("upload_progress", 0)
            
            if progress != prev_progress:
                print(f"Status: {status}, Progress: {progress}%")
                prev_progress = progress
            
            if status == "completed" or status == "failed":
                print(f"Final Status: {status}, Final Progress: {progress}%")
                break
                
            await asyncio.sleep(0.5)
            
        if status == "completed":
            print("SUCCESS: Upload completed.")
        else:
            print("FAILURE: Upload failed.")

if __name__ == "__main__":
    asyncio.run(main())
