
import asyncio
import httpx
import sys

# Configuration
BASE_URL = "http://localhost:8002"
EMAIL = "admin@example.com"
PASSWORD = "admin123456"

async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Login to get token
        print("1. Logging in...")
        try:
            response = await client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
            if response.status_code != 200:
                print(f"Login failed: {response.status_code} - {response.text}")
                # Try creating the user if it doesn't exist (e.g. if DB was empty)
                # But actually, users should be seeded. 
                return

            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print(f"✓ Login successful")
        except Exception as e:
            print(f"Login error: {e}")
            return

        # 2. Create Category
        print("\n2. Creating Category...")
        cat_name = "Test Category"
        response = await client.post("/pod-categories", json={"name": cat_name}, headers=headers)
        if response.status_code == 201:
            data = response.json()
            cat_id = data["id"]
            print(f"✓ Category created: {data}")
        elif response.status_code == 400 and "already exists" in response.text:
             print("Category already exists, fetching it...")
             # Fetch list to find ID
             list_res = await client.get("/pod-categories", headers=headers)
             for c in list_res.json():
                 if c["name"] == cat_name:
                     cat_id = c["id"]
                     print(f"✓ Found existing category ID: {cat_id}")
                     break
             else:
                 print("Could not find existing category?")
                 return
        else:
            print(f"Failed to create category: {response.status_code} - {response.text}")
            return

        # 3. List Categories
        print("\n3. Listing Categories...")
        response = await client.get("/pod-categories", headers=headers)
        if response.status_code == 200:
            cats = response.json()
            print(f"✓ Found {len(cats)} categories")
            print(cats)
        else:
            print(f"Failed to list categories: {response.status_code} - {response.text}")

        # 4. Get Category
        print(f"\n4. Getting Category {cat_id}...")
        response = await client.get(f"/pod-categories/{cat_id}", headers=headers)
        if response.status_code == 200:
             print(f"✓ Got category: {response.json()}")
        else:
             print(f"Failed to get category: {response.status_code} - {response.text}")

        # 5. Update Category
        print(f"\n5. Updating Category {cat_id}...")
        new_name = "Updated Test Category"
        response = await client.patch(f"/pod-categories/{cat_id}", json={"name": new_name}, headers=headers)
        if response.status_code == 200:
            print(f"✓ Updated category: {response.json()}")
        else:
            print(f"Failed to update category: {response.status_code} - {response.text}")

        # 6. Delete Category
        print(f"\n6. Deleting Category {cat_id}...")
        response = await client.delete(f"/pod-categories/{cat_id}", headers=headers)
        if response.status_code == 204:
            print(f"✓ Deleted category")
        else:
            print(f"Failed to delete category: {response.status_code} - {response.text}")

        # 7. Verify Deletion
        print("\n7. Verifying Deletion...")
        response = await client.get(f"/pod-categories/{cat_id}", headers=headers)
        if response.status_code == 404:
            print(f"✓ Category correctly not found")
        else:
             print(f"Category still exists or error: {response.status_code}")

if __name__ == "__main__":
    asyncio.run(main())
