
import asyncio
import httpx
import sys

BASE_URL = "http://localhost:8002"
ADMIN_EMAIL = "superadmin@example.com"
ADMIN_PASSWORD = "secret123"

async def verify_usage():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Login as Admin
        print("Logging in as Admin...")
        try:
            resp = await client.post(f"{BASE_URL}/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            })
            if resp.status_code != 200:
                print(f"Login failed: {resp.status_code} {resp.text}")
                # Try creating admin if not exists (harder in script without DB access logic here)
                # Assuming admin exists from previous setup or seeds
                return
            
            token = resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print("Login successful.")

            # 2. Call Usage API
            print("Calling GET /users/usage...")
            resp = await client.get(f"{BASE_URL}/users/usage", headers=headers)
            
            if resp.status_code == 200:
                data = resp.json()
                print("Usage API Response:")
                import json
                print(json.dumps(data, indent=2))
                
                if isinstance(data, list):
                    print(f"Found {len(data)} users.")
                
                # 3. Test Filtering
                print("\nTesting Filter by user_id=1...")
                resp_filter = await client.get(f"{BASE_URL}/users/usage?user_id=1", headers=headers)
                if resp_filter.status_code == 200:
                    data_filter = resp_filter.json()
                    print(f"Filtered Response: Found {len(data_filter)} users.")
                    if len(data_filter) == 1 and data_filter[0]['id'] == 1:
                        print("SUCCESS: Filtering by user_id works.")
                    else:
                         print(f"FAILURE: Filtering returned {len(data_filter)} users or wrong ID.")
                         if len(data_filter) > 0:
                             print(f"Returned ID: {data_filter[0]['id']}")
                else:
                    print(f"Error testing filter: {resp_filter.status_code}")
                    
            elif resp.status_code == 403:
                print("Error: Admin privileges required (403). Check user role.")
            else:
                print(f"Error calling API: {resp.status_code} {resp.text}")

        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(verify_usage())
